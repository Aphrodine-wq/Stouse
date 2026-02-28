import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db
from vibehouse.common.enums import (
    ContractStatus,
    DisputeStatus,
    PhaseType,
    ProjectStatus,
    TaskStatus,
    UserRole,
)
from vibehouse.common.exceptions import NotFoundError, PermissionDeniedError
from vibehouse.db.models.audit import AuditLog
from vibehouse.db.models.change_order import ChangeOrder
from vibehouse.db.models.contract import Contract
from vibehouse.db.models.dispute import Dispute
from vibehouse.db.models.phase import ProjectPhase
from vibehouse.db.models.project import Project
from vibehouse.db.models.report import DailyReport
from vibehouse.db.models.task import Task
from vibehouse.db.models.user import User

router = APIRouter(prefix="/projects/{project_id}", tags=["Dashboard"])


# ---------- Schemas ----------


class ProjectSummary(BaseModel):
    id: uuid.UUID
    title: str
    status: str
    owner_name: str
    address: str | None
    budget: Decimal | None
    budget_spent: Decimal
    budget_remaining: Decimal | None
    created_at: str
    days_active: int


class PhaseProgress(BaseModel):
    phase_type: str
    status: str
    task_count: int
    completed_count: int
    percent_complete: float
    budget_allocated: Decimal | None
    budget_spent: Decimal


class TaskSummary(BaseModel):
    total: int
    by_status: dict[str, int]
    overdue_count: int
    due_this_week: int


class FinancialSummary(BaseModel):
    total_budget: Decimal | None
    total_committed: Decimal
    total_spent: Decimal
    projected_total: Decimal
    variance_percent: float | None
    alert_level: str  # "green", "yellow", "red"


class TimelineOverview(BaseModel):
    start_date: str | None
    estimated_completion: str | None
    percent_complete: float
    critical_path_items: list[str]
    days_ahead_behind: int


class ActivityEntry(BaseModel):
    timestamp: str
    description: str
    actor: str | None
    type: str


class DashboardResponse(BaseModel):
    project_summary: ProjectSummary
    phase_progress: list[PhaseProgress]
    task_summary: TaskSummary
    financial_summary: FinancialSummary
    timeline: TimelineOverview
    recent_activity: list[ActivityEntry]
    active_disputes: int
    active_change_orders: int
    pending_decisions: int
    weather_note: str | None


# ---------- Endpoints ----------


@router.get("/dashboard", response_model=DashboardResponse)
async def get_project_dashboard(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _verify_project_access(project_id, current_user, db)

    # Fetch all phases for this project
    phases_result = await db.execute(
        select(ProjectPhase)
        .where(ProjectPhase.project_id == project_id, ProjectPhase.is_deleted.is_(False))
        .order_by(ProjectPhase.order_index)
    )
    phases = phases_result.scalars().all()
    phase_ids = [p.id for p in phases]

    # Fetch all tasks across all phases
    tasks: list[Task] = []
    if phase_ids:
        tasks_result = await db.execute(
            select(Task).where(Task.phase_id.in_(phase_ids), Task.is_deleted.is_(False))
        )
        tasks = list(tasks_result.scalars().all())

    # Fetch contracts
    contracts_result = await db.execute(
        select(Contract).where(
            Contract.project_id == project_id, Contract.is_deleted.is_(False)
        )
    )
    contracts = contracts_result.scalars().all()

    # Fetch active disputes count
    active_dispute_statuses = [
        DisputeStatus.IDENTIFIED.value,
        DisputeStatus.DIRECT_RESOLUTION.value,
        DisputeStatus.AI_MEDIATION.value,
        DisputeStatus.EXTERNAL_MEDIATION.value,
    ]
    disputes_count_result = await db.execute(
        select(func.count(Dispute.id)).where(
            Dispute.project_id == project_id,
            Dispute.is_deleted.is_(False),
            Dispute.status.in_(active_dispute_statuses),
        )
    )
    active_disputes = disputes_count_result.scalar() or 0

    # Fetch active change orders count (pending or approved but not yet implemented)
    change_orders_result = await db.execute(
        select(func.count(ChangeOrder.id)).where(
            ChangeOrder.project_id == project_id,
            ChangeOrder.is_deleted.is_(False),
            ChangeOrder.status.in_(["pending", "approved"]),
        )
    )
    active_change_orders = change_orders_result.scalar() or 0

    # Pending decisions: pending change orders + disputes awaiting homeowner response
    pending_co_result = await db.execute(
        select(func.count(ChangeOrder.id)).where(
            ChangeOrder.project_id == project_id,
            ChangeOrder.is_deleted.is_(False),
            ChangeOrder.status == "pending",
        )
    )
    pending_co = pending_co_result.scalar() or 0

    pending_dispute_result = await db.execute(
        select(func.count(Dispute.id)).where(
            Dispute.project_id == project_id,
            Dispute.is_deleted.is_(False),
            Dispute.status == DisputeStatus.IDENTIFIED.value,
        )
    )
    pending_disputes = pending_dispute_result.scalar() or 0
    pending_decisions = pending_co + pending_disputes

    # Fetch recent audit log entries
    audit_result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.entity_type == "project",
            AuditLog.entity_id == project_id,
            AuditLog.is_deleted.is_(False),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    )
    audit_entries = audit_result.scalars().all()

    # Build project summary
    now = datetime.utcnow()
    days_active = (now - project.created_at.replace(tzinfo=None)).days if project.created_at else 0
    owner_name = project.owner.full_name if project.owner else "Unknown"
    budget_remaining = (
        (project.budget - project.budget_spent) if project.budget is not None else None
    )

    project_summary = ProjectSummary(
        id=project.id,
        title=project.title,
        status=project.status,
        owner_name=owner_name,
        address=project.address,
        budget=project.budget,
        budget_spent=project.budget_spent,
        budget_remaining=budget_remaining,
        created_at=project.created_at.isoformat(),
        days_active=days_active,
    )

    # Build phase progress
    # Group tasks by phase
    tasks_by_phase: dict[uuid.UUID, list[Task]] = {}
    for t in tasks:
        tasks_by_phase.setdefault(t.phase_id, []).append(t)

    phase_progress_list: list[PhaseProgress] = []
    for phase in phases:
        phase_tasks = tasks_by_phase.get(phase.id, [])
        task_count = len(phase_tasks)
        completed_count = sum(
            1 for t in phase_tasks if t.status == TaskStatus.COMPLETED.value
        )
        percent_complete = (
            round((completed_count / task_count) * 100, 1) if task_count > 0 else 0.0
        )

        phase_progress_list.append(
            PhaseProgress(
                phase_type=phase.phase_type,
                status=phase.status,
                task_count=task_count,
                completed_count=completed_count,
                percent_complete=percent_complete,
                budget_allocated=phase.budget_allocated,
                budget_spent=phase.budget_spent,
            )
        )

    # Build task summary
    today = date.today()
    week_end = today + timedelta(days=(6 - today.weekday()))  # End of current week (Sunday)

    by_status: dict[str, int] = {}
    overdue_count = 0
    due_this_week = 0
    for t in tasks:
        status_key = t.status if isinstance(t.status, str) else t.status
        by_status[status_key] = by_status.get(status_key, 0) + 1
        if (
            t.due_date is not None
            and t.due_date < today
            and t.status != TaskStatus.COMPLETED.value
        ):
            overdue_count += 1
        if (
            t.due_date is not None
            and today <= t.due_date <= week_end
            and t.status != TaskStatus.COMPLETED.value
        ):
            due_this_week += 1

    task_summary = TaskSummary(
        total=len(tasks),
        by_status=by_status,
        overdue_count=overdue_count,
        due_this_week=due_this_week,
    )

    # Build financial summary
    total_committed = sum(
        (c.amount for c in contracts if c.status in (
            ContractStatus.ACCEPTED.value,
            ContractStatus.ACTIVE.value,
            ContractStatus.COMPLETED.value,
        )),
        Decimal("0.00"),
    )
    total_spent = project.budget_spent

    # Simple projected total: if we have a burn rate, project forward
    if project.budget and project.budget > 0:
        total_tasks = len(tasks)
        completed_tasks = sum(
            1 for t in tasks if t.status == TaskStatus.COMPLETED.value
        )
        if completed_tasks > 0 and total_tasks > 0:
            progress_ratio = completed_tasks / total_tasks
            projected_total = (
                total_spent / Decimal(str(progress_ratio))
                if progress_ratio > 0
                else total_committed
            )
        else:
            projected_total = max(total_committed, total_spent)

        variance_percent = round(
            float((projected_total - project.budget) / project.budget * 100), 1
        )
        if variance_percent > 10:
            alert_level = "red"
        elif variance_percent > 5:
            alert_level = "yellow"
        else:
            alert_level = "green"
    else:
        projected_total = max(total_committed, total_spent)
        variance_percent = None
        alert_level = "green"

    financial_summary = FinancialSummary(
        total_budget=project.budget,
        total_committed=total_committed,
        total_spent=total_spent,
        projected_total=projected_total,
        variance_percent=variance_percent,
        alert_level=alert_level,
    )

    # Build timeline overview
    phase_start_dates = [p.start_date for p in phases if p.start_date is not None]
    phase_end_dates = [p.end_date for p in phases if p.end_date is not None]
    overall_start = min(phase_start_dates) if phase_start_dates else None
    overall_end = max(phase_end_dates) if phase_end_dates else None

    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED.value)
    overall_percent = (
        round((completed_tasks / total_tasks) * 100, 1) if total_tasks > 0 else 0.0
    )

    # Estimate days ahead/behind based on expected linear progress
    days_ahead_behind = 0
    if overall_start and overall_end and overall_start < overall_end:
        total_duration = (overall_end - overall_start).days
        elapsed = (today - overall_start).days
        if total_duration > 0 and elapsed > 0:
            expected_percent = min((elapsed / total_duration) * 100, 100.0)
            difference = overall_percent - expected_percent
            days_ahead_behind = round(difference * total_duration / 100)

    # Critical path: tasks that are incomplete and have the latest due dates
    incomplete_with_dates = [
        t for t in tasks
        if t.status != TaskStatus.COMPLETED.value and t.due_date is not None
    ]
    incomplete_with_dates.sort(key=lambda t: t.due_date, reverse=True)
    critical_path_items = [t.title for t in incomplete_with_dates[:5]]

    timeline_overview = TimelineOverview(
        start_date=overall_start.isoformat() if overall_start else None,
        estimated_completion=overall_end.isoformat() if overall_end else None,
        percent_complete=overall_percent,
        critical_path_items=critical_path_items,
        days_ahead_behind=days_ahead_behind,
    )

    # Build recent activity from audit log
    recent_activity: list[ActivityEntry] = []
    for entry in audit_entries:
        recent_activity.append(
            ActivityEntry(
                timestamp=entry.created_at.isoformat(),
                description=f"{entry.action} on {entry.entity_type}",
                actor=str(entry.actor_id) if entry.actor_id else None,
                type=entry.action,
            )
        )

    # Also add recently changed tasks (completed or updated in last 7 days)
    recent_cutoff = now - timedelta(days=7)
    recent_tasks = [
        t for t in tasks
        if t.updated_at and t.updated_at.replace(tzinfo=None) > recent_cutoff
    ]
    recent_tasks.sort(key=lambda t: t.updated_at, reverse=True)
    for t in recent_tasks[:10 - len(recent_activity)]:
        recent_activity.append(
            ActivityEntry(
                timestamp=t.updated_at.isoformat(),
                description=f"Task '{t.title}' updated to {t.status}",
                actor=str(t.assignee_id) if t.assignee_id else None,
                type="task_update",
            )
        )

    # Sort all activity by timestamp descending, keep only 10
    recent_activity.sort(key=lambda a: a.timestamp, reverse=True)
    recent_activity = recent_activity[:10]

    # Mock weather note
    weather_note: str | None = None
    if project.address:
        weather_note = "Partly cloudy, 72\u00b0F. Good conditions for exterior work."

    return DashboardResponse(
        project_summary=project_summary,
        phase_progress=phase_progress_list,
        task_summary=task_summary,
        financial_summary=financial_summary,
        timeline=timeline_overview,
        recent_activity=recent_activity,
        active_disputes=active_disputes,
        active_change_orders=active_change_orders,
        pending_decisions=pending_decisions,
        weather_note=weather_note,
    )


async def _verify_project_access(
    project_id: uuid.UUID, user: User, db: AsyncSession
) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))
    if user.role != UserRole.ADMIN.value and project.owner_id != user.id:
        raise PermissionDeniedError("You do not have access to this project")
    return project
