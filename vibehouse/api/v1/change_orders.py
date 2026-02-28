import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel as PydanticModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db
from vibehouse.common.enums import UserRole
from vibehouse.common.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from vibehouse.db.models.change_order import ChangeOrder
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User

router = APIRouter(prefix="/change-orders", tags=["Change Orders"])

VALID_STATUSES = {"proposed", "under_review", "approved", "rejected", "implemented"}
VALID_TRANSITIONS = {
    "proposed": ["under_review", "rejected"],
    "under_review": ["approved", "rejected"],
    "approved": ["implemented"],
    "rejected": [],
    "implemented": [],
}


# ---------- Schemas ----------


class CreateChangeOrderRequest(PydanticModel):
    project_id: uuid.UUID
    contract_id: uuid.UUID | None = None
    title: str
    description: str
    reason: str = "scope_change"
    cost_impact: Decimal = Decimal("0.00")
    timeline_impact_days: int = 0
    items: list[dict] = []


class ChangeOrderResponse(PydanticModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str
    reason: str
    cost_impact: Decimal
    timeline_impact_days: int
    status: str
    created_at: str
    model_config = {"from_attributes": True}


class UpdateStatusRequest(PydanticModel):
    status: str


# ---------- Endpoints ----------


@router.post("", response_model=ChangeOrderResponse, status_code=201)
async def create_change_order(
    body: CreateChangeOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == body.project_id, Project.is_deleted.is_(False))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(body.project_id))
    if current_user.role != UserRole.ADMIN.value and project.owner_id != current_user.id:
        raise PermissionDeniedError("You do not have access to this project")

    co = ChangeOrder(
        project_id=body.project_id,
        contract_id=body.contract_id,
        requested_by=current_user.id,
        title=body.title,
        description=body.description,
        reason=body.reason,
        cost_impact=body.cost_impact,
        timeline_impact_days=body.timeline_impact_days,
        items=body.items,
    )
    db.add(co)
    await db.flush()
    await db.refresh(co)
    return ChangeOrderResponse(
        id=co.id, project_id=co.project_id, title=co.title, description=co.description,
        reason=co.reason, cost_impact=co.cost_impact,
        timeline_impact_days=co.timeline_impact_days, status=co.status,
        created_at=co.created_at.isoformat(),
    )


@router.get("/{project_id}", response_model=list[ChangeOrderResponse])
async def list_change_orders(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChangeOrder).where(
            ChangeOrder.project_id == project_id, ChangeOrder.is_deleted.is_(False)
        ).order_by(ChangeOrder.created_at.desc())
    )
    orders = result.scalars().all()
    return [
        ChangeOrderResponse(
            id=co.id, project_id=co.project_id, title=co.title, description=co.description,
            reason=co.reason, cost_impact=co.cost_impact,
            timeline_impact_days=co.timeline_impact_days, status=co.status,
            created_at=co.created_at.isoformat(),
        )
        for co in orders
    ]


@router.patch("/{change_order_id}/status", response_model=ChangeOrderResponse)
async def update_status(
    change_order_id: uuid.UUID,
    body: UpdateStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChangeOrder).where(ChangeOrder.id == change_order_id, ChangeOrder.is_deleted.is_(False))
    )
    co = result.scalar_one_or_none()
    if not co:
        raise NotFoundError("Change Order", str(change_order_id))

    allowed = VALID_TRANSITIONS.get(co.status, [])
    if body.status not in allowed:
        raise BadRequestError(f"Cannot transition from '{co.status}' to '{body.status}'")

    co.status = body.status
    await db.flush()
    await db.refresh(co)
    return ChangeOrderResponse(
        id=co.id, project_id=co.project_id, title=co.title, description=co.description,
        reason=co.reason, cost_impact=co.cost_impact,
        timeline_impact_days=co.timeline_impact_days, status=co.status,
        created_at=co.created_at.isoformat(),
    )
