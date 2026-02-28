"""Change order management for construction projects."""

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db, require_role
from vibehouse.common.enums import UserRole
from vibehouse.common.events import emit
from vibehouse.common.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from vibehouse.common.pagination import PaginatedResponse, PaginationParams, paginate
from vibehouse.db.models.change_order import ChangeOrder
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User

router = APIRouter(prefix="/projects/{project_id}/change-orders", tags=["Change Orders"])


# ---------- Schemas ----------

class ChangeOrderCreate(BaseModel):
    title: str
    description: str
    reason: str  # scope_change, error, client_request, unforeseen
    cost_impact: Decimal = Decimal("0.00")
    schedule_impact_days: int = 0
    affected_phases: list[str] | None = None


class ChangeOrderUpdate(BaseModel):
    action: str  # approve, reject, implement
    notes: str | None = None


class ChangeOrderResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    requested_by_id: uuid.UUID
    title: str
    description: str
    reason: str
    cost_impact: Decimal
    schedule_impact_days: int
    status: str
    affected_phases: list | None
    approval_chain: list | None
    created_at: str
    model_config = {"from_attributes": True}


class ChangeOrderListResponse(PaginatedResponse[ChangeOrderResponse]):
    pass


VALID_REASONS = {"scope_change", "error", "client_request", "unforeseen"}
VALID_TRANSITIONS = {
    "pending": ["approved", "rejected"],
    "approved": ["implemented"],
    "rejected": [],
    "implemented": [],
}


# ---------- Endpoints ----------

@router.post("", response_model=ChangeOrderResponse, status_code=201)
async def create_change_order(
    project_id: uuid.UUID,
    body: ChangeOrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_access(project_id, current_user, db)

    if body.reason not in VALID_REASONS:
        raise BadRequestError(f"reason must be one of: {', '.join(sorted(VALID_REASONS))}")

    co = ChangeOrder(
        project_id=project_id,
        requested_by_id=current_user.id,
        title=body.title,
        description=body.description,
        reason=body.reason,
        cost_impact=body.cost_impact,
        schedule_impact_days=body.schedule_impact_days,
        affected_phases=body.affected_phases or [],
        approval_chain=[{
            "action": "submitted",
            "by": str(current_user.id),
            "by_name": current_user.full_name,
        }],
    )
    db.add(co)
    await db.flush()
    await db.refresh(co)

    await emit(str(project_id), "change_order.created", {
        "change_order_id": str(co.id),
        "title": co.title,
        "cost_impact": str(co.cost_impact),
        "requested_by": current_user.full_name,
    })

    return _co_response(co)


@router.get("", response_model=ChangeOrderListResponse)
async def list_change_orders(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    params: PaginationParams = Depends(),
):
    await _verify_access(project_id, current_user, db)
    query = (
        select(ChangeOrder)
        .where(ChangeOrder.project_id == project_id, ChangeOrder.is_deleted.is_(False))
        .order_by(ChangeOrder.created_at.desc())
    )
    items, total = await paginate(db, query, params, ChangeOrder)
    total_pages = (total + params.page_size - 1) // params.page_size
    return ChangeOrderListResponse(
        items=[_co_response(c) for c in items],
        total=total, page=params.page, page_size=params.page_size, total_pages=total_pages,
    )


@router.patch("/{co_id}", response_model=ChangeOrderResponse)
async def update_change_order(
    project_id: uuid.UUID,
    co_id: uuid.UUID,
    body: ChangeOrderUpdate,
    current_user: User = Depends(require_role(UserRole.HOMEOWNER, UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    await _verify_access(project_id, current_user, db)

    result = await db.execute(
        select(ChangeOrder).where(
            ChangeOrder.id == co_id,
            ChangeOrder.project_id == project_id,
            ChangeOrder.is_deleted.is_(False),
        )
    )
    co = result.scalar_one_or_none()
    if not co:
        raise NotFoundError("Change order", str(co_id))

    action_map = {"approve": "approved", "reject": "rejected", "implement": "implemented"}
    new_status = action_map.get(body.action)
    if not new_status:
        raise BadRequestError(f"action must be one of: approve, reject, implement")

    allowed = VALID_TRANSITIONS.get(co.status, [])
    if new_status not in allowed:
        raise BadRequestError(f"Cannot transition from '{co.status}' to '{new_status}'")

    co.status = new_status
    chain = co.approval_chain or []
    chain.append({
        "action": body.action,
        "by": str(current_user.id),
        "by_name": current_user.full_name,
        "notes": body.notes,
    })
    co.approval_chain = chain

    # If implemented, adjust project budget
    if new_status == "implemented" and co.cost_impact:
        project_result = await db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one()
        if project.budget:
            project.budget = project.budget + co.cost_impact

    await db.flush()
    await db.refresh(co)

    await emit(str(project_id), f"change_order.{body.action}d", {
        "change_order_id": str(co.id),
        "title": co.title,
        "new_status": new_status,
        "by": current_user.full_name,
    })

    return _co_response(co)


def _co_response(co: ChangeOrder) -> ChangeOrderResponse:
    return ChangeOrderResponse(
        id=co.id, project_id=co.project_id, requested_by_id=co.requested_by_id,
        title=co.title, description=co.description, reason=co.reason,
        cost_impact=co.cost_impact, schedule_impact_days=co.schedule_impact_days,
        status=co.status, affected_phases=co.affected_phases,
        approval_chain=co.approval_chain, created_at=co.created_at.isoformat(),
    )


async def _verify_access(project_id: uuid.UUID, user: User, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))
    if user.role != UserRole.ADMIN.value and project.owner_id != user.id:
        raise PermissionDeniedError("You do not have access to this project")
    return project
