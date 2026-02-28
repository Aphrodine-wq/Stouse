import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel as PydanticModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_db, require_role
from vibehouse.common.enums import ProjectStatus, UserRole
from vibehouse.db.models.change_order import ChangeOrder
from vibehouse.db.models.dispute import Dispute
from vibehouse.db.models.payment import Invoice, Payment
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User

router = APIRouter(prefix="/admin", tags=["Admin"])


# ---------- Schemas ----------


class PlatformStatsResponse(PydanticModel):
    total_users: int
    total_projects: int
    active_projects: int
    total_revenue: float
    total_invoiced: float
    open_disputes: int
    pending_change_orders: int
    users_by_role: dict[str, int]
    projects_by_status: dict[str, int]


class UserAdminResponse(PydanticModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    project_count: int
    created_at: str
    model_config = {"from_attributes": True}


# ---------- Endpoints ----------


@router.get("/stats", response_model=PlatformStatsResponse)
async def platform_stats(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    # Users
    users_result = await db.execute(select(User).where(User.is_deleted.is_(False)))
    users = users_result.scalars().all()
    total_users = len(users)
    users_by_role: dict[str, int] = {}
    for u in users:
        users_by_role[u.role] = users_by_role.get(u.role, 0) + 1

    # Projects
    projects_result = await db.execute(select(Project).where(Project.is_deleted.is_(False)))
    projects = projects_result.scalars().all()
    total_projects = len(projects)
    active_projects = sum(1 for p in projects if p.status in (ProjectStatus.IN_PROGRESS.value, ProjectStatus.PLANNING.value, ProjectStatus.DESIGNING.value))
    projects_by_status: dict[str, int] = {}
    for p in projects:
        projects_by_status[p.status] = projects_by_status.get(p.status, 0) + 1

    # Payments
    payments_result = await db.execute(
        select(Payment).where(Payment.is_deleted.is_(False), Payment.status == "succeeded")
    )
    payments = payments_result.scalars().all()
    total_revenue = float(sum(p.amount for p in payments))

    # Invoices
    invoices_result = await db.execute(select(Invoice).where(Invoice.is_deleted.is_(False)))
    invoices = invoices_result.scalars().all()
    total_invoiced = float(sum(inv.amount for inv in invoices))

    # Disputes
    disputes_result = await db.execute(
        select(Dispute).where(
            Dispute.is_deleted.is_(False),
            Dispute.status.notin_(["resolved", "closed"]),
        )
    )
    open_disputes = len(disputes_result.scalars().all())

    # Change orders
    co_result = await db.execute(
        select(ChangeOrder).where(
            ChangeOrder.is_deleted.is_(False),
            ChangeOrder.status.in_(["proposed", "under_review"]),
        )
    )
    pending_cos = len(co_result.scalars().all())

    return PlatformStatsResponse(
        total_users=total_users,
        total_projects=total_projects,
        active_projects=active_projects,
        total_revenue=total_revenue,
        total_invoiced=total_invoiced,
        open_disputes=open_disputes,
        pending_change_orders=pending_cos,
        users_by_role=users_by_role,
        projects_by_status=projects_by_status,
    )


@router.get("/users", response_model=list[UserAdminResponse])
async def list_all_users(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.is_deleted.is_(False)).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    responses = []
    for u in users:
        proj_result = await db.execute(
            select(Project).where(Project.owner_id == u.id, Project.is_deleted.is_(False))
        )
        project_count = len(proj_result.scalars().all())
        responses.append(UserAdminResponse(
            id=u.id, email=u.email, full_name=u.full_name, role=u.role,
            is_active=u.is_active, project_count=project_count,
            created_at=u.created_at.isoformat(),
        ))
    return responses


@router.patch("/users/{user_id}/deactivate", status_code=204)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.is_active = False
        await db.flush()


@router.patch("/users/{user_id}/activate", status_code=204)
async def activate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        user.is_active = True
        await db.flush()
