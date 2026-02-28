from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.common.logging import get_logger
from vibehouse.core.reporting.schemas import BudgetSummary
from vibehouse.db.models.phase import ProjectPhase
from vibehouse.db.models.project import Project

logger = get_logger("reporting.budget_tracker")


async def get_budget_summary(project: Project, db: AsyncSession) -> BudgetSummary:
    result = await db.execute(
        select(ProjectPhase).where(
            ProjectPhase.project_id == project.id,
            ProjectPhase.is_deleted.is_(False),
        )
    )
    phases = result.scalars().all()

    total_spent = sum((p.budget_spent for p in phases), Decimal("0.00"))

    remaining = None
    burn_rate = None
    alert_level = "green"

    if project.budget and project.budget > 0:
        remaining = project.budget - total_spent
        burn_rate = float(total_spent / project.budget * 100)

        if burn_rate >= 100:
            alert_level = "red"
        elif burn_rate >= 90:
            alert_level = "red"
        elif burn_rate >= 75:
            alert_level = "yellow"

    return BudgetSummary(
        total_budget=project.budget,
        total_spent=total_spent,
        remaining=remaining,
        burn_rate_percent=burn_rate,
        alert_level=alert_level,
    )


def check_budget_thresholds(summary: BudgetSummary) -> list[str]:
    alerts = []

    if summary.burn_rate_percent is not None:
        if summary.burn_rate_percent >= 100:
            alerts.append("CRITICAL: Budget has been exceeded!")
        elif summary.burn_rate_percent >= 90:
            alerts.append("WARNING: 90% of budget has been spent")
        elif summary.burn_rate_percent >= 75:
            alerts.append("NOTICE: 75% of budget has been spent")

    return alerts
