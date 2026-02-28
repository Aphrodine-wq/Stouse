from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.common.enums import TaskStatus
from vibehouse.common.logging import get_logger
from vibehouse.core.reporting.schemas import (
    DailyReportContent,
    RiskAlert,
    ScheduleHealth,
    TaskProgressSummary,
)
from vibehouse.db.models.phase import ProjectPhase
from vibehouse.db.models.project import Project
from vibehouse.db.models.task import Task

logger = get_logger("reporting.daily_report")


async def compile_daily_report(project: Project, db: AsyncSession) -> DailyReportContent:
    # Get all phases and tasks
    result = await db.execute(
        select(ProjectPhase).where(
            ProjectPhase.project_id == project.id,
            ProjectPhase.is_deleted.is_(False),
        )
    )
    phases = result.scalars().all()

    all_tasks = []
    for phase in phases:
        task_result = await db.execute(
            select(Task).where(Task.phase_id == phase.id, Task.is_deleted.is_(False))
        )
        all_tasks.extend(task_result.scalars().all())

    # Task progress
    total = len(all_tasks)
    completed = sum(1 for t in all_tasks if t.status == TaskStatus.COMPLETED.value)
    in_progress = sum(1 for t in all_tasks if t.status == TaskStatus.IN_PROGRESS.value)
    blocked = sum(1 for t in all_tasks if t.status == TaskStatus.BLOCKED.value)
    completion_pct = (completed / total * 100) if total > 0 else 0

    task_progress = TaskProgressSummary(
        total_tasks=total,
        completed=completed,
        in_progress=in_progress,
        blocked=blocked,
        completion_percent=round(completion_pct, 1),
    )

    # Schedule health
    schedule_health = ScheduleHealth(
        days_elapsed=0,
        estimated_total_days=180,
        percent_complete=completion_pct,
        days_ahead_behind=0,
        status="on_track" if blocked == 0 else "at_risk",
    )

    # Risk alerts
    risk_alerts = []
    if blocked > 0:
        risk_alerts.append(
            RiskAlert(
                severity="high" if blocked > 2 else "medium",
                category="blocked_tasks",
                message=f"{blocked} task(s) are currently blocked",
            )
        )

    # Activities today
    activities = []
    if in_progress > 0:
        active_tasks = [t for t in all_tasks if t.status == TaskStatus.IN_PROGRESS.value]
        for t in active_tasks[:5]:
            activities.append(f"In progress: {t.title}")

    completed_today = [
        t for t in all_tasks
        if t.status == TaskStatus.COMPLETED.value
        and t.updated_at
        and t.updated_at.date() == date.today()
    ]
    for t in completed_today[:5]:
        activities.append(f"Completed: {t.title}")

    if not activities:
        activities.append("No active tasks today")

    # Upcoming milestones
    milestones = []
    for phase in phases:
        if phase.status != TaskStatus.COMPLETED.value:
            milestones.append(f"{phase.phase_type} phase")
            if len(milestones) >= 3:
                break

    # Executive summary
    summary = (
        f"Project is {completion_pct:.0f}% complete with {completed}/{total} tasks done. "
        f"{in_progress} tasks in progress"
    )
    if blocked > 0:
        summary += f", {blocked} blocked"
    summary += "."

    from vibehouse.core.reporting.budget_tracker import get_budget_summary

    budget_summary = await get_budget_summary(project, db)

    return DailyReportContent(
        date=date.today().isoformat(),
        project_title=project.title,
        executive_summary=summary,
        task_progress=task_progress,
        budget_summary=budget_summary,
        schedule_health=schedule_health,
        activities_today=activities,
        risk_alerts=risk_alerts,
        upcoming_milestones=milestones,
    )
