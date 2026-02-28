import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db
from vibehouse.common.enums import UserRole
from vibehouse.common.exceptions import NotFoundError, PermissionDeniedError
from vibehouse.db.models.phase import ProjectPhase
from vibehouse.db.models.project import Project
from vibehouse.db.models.report import DailyReport
from vibehouse.db.models.user import User

router = APIRouter(prefix="/projects/{project_id}", tags=["Reports"])


# ---------- Schemas ----------


class DailyReportResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    report_date: str
    summary: str | None
    content: dict
    pdf_url: str | None
    sent_at: str | None
    created_at: str

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    reports: list[DailyReportResponse]
    total: int


class BudgetPhaseBreakdown(BaseModel):
    phase: str
    allocated: Decimal | None
    spent: Decimal
    remaining: Decimal | None


class BudgetResponse(BaseModel):
    project_id: uuid.UUID
    total_budget: Decimal | None
    total_spent: Decimal
    remaining: Decimal | None
    burn_rate_percent: float | None
    phases: list[BudgetPhaseBreakdown]


# ---------- Endpoints ----------


@router.get("/reports/daily", response_model=ReportListResponse)
async def list_daily_reports(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(DailyReport)
        .where(DailyReport.project_id == project_id, DailyReport.is_deleted.is_(False))
        .order_by(DailyReport.report_date.desc())
    )
    reports = result.scalars().all()

    return ReportListResponse(
        reports=[_report_to_response(r) for r in reports],
        total=len(reports),
    )


@router.get("/reports/daily/latest", response_model=DailyReportResponse)
async def get_latest_report(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(DailyReport)
        .where(DailyReport.project_id == project_id, DailyReport.is_deleted.is_(False))
        .order_by(DailyReport.report_date.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundError("Daily report")

    return _report_to_response(report)


@router.get("/budget", response_model=BudgetResponse)
async def get_budget(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _verify_project_access(project_id, current_user, db)

    result = await db.execute(
        select(ProjectPhase)
        .where(ProjectPhase.project_id == project_id, ProjectPhase.is_deleted.is_(False))
        .order_by(ProjectPhase.order_index)
    )
    phases = result.scalars().all()

    total_spent = sum((p.budget_spent for p in phases), Decimal("0.00"))
    remaining = (project.budget - total_spent) if project.budget else None
    burn_rate = (
        float(total_spent / project.budget * 100) if project.budget and project.budget > 0 else None
    )

    phase_breakdowns = [
        BudgetPhaseBreakdown(
            phase=p.phase_type,
            allocated=p.budget_allocated,
            spent=p.budget_spent,
            remaining=(p.budget_allocated - p.budget_spent) if p.budget_allocated else None,
        )
        for p in phases
    ]

    return BudgetResponse(
        project_id=project_id,
        total_budget=project.budget,
        total_spent=total_spent,
        remaining=remaining,
        burn_rate_percent=burn_rate,
        phases=phase_breakdowns,
    )


def _report_to_response(report: DailyReport) -> DailyReportResponse:
    return DailyReportResponse(
        id=report.id,
        project_id=report.project_id,
        report_date=report.report_date.isoformat(),
        summary=report.summary,
        content=report.content,
        pdf_url=report.pdf_url,
        sent_at=report.sent_at.isoformat() if report.sent_at else None,
        created_at=report.created_at.isoformat(),
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
