import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.common.logging import get_logger
from vibehouse.core.reporting.budget_tracker import get_budget_summary
from vibehouse.core.reporting.daily_report import compile_daily_report
from vibehouse.db.models.project import Project
from vibehouse.db.models.report import DailyReport

logger = get_logger("reporting.service")


class ReportingService:
    async def generate_daily_report(self, project_id: str, db: AsyncSession) -> DailyReport:
        result = await db.execute(
            select(Project).where(Project.id == uuid.UUID(project_id))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Compile report content
        report_content = await compile_daily_report(project, db)

        # Create DB record
        report = DailyReport(
            project_id=uuid.UUID(project_id),
            report_date=date.today(),
            content=report_content.model_dump(mode="json"),
            summary=report_content.executive_summary,
        )
        db.add(report)
        await db.flush()
        await db.refresh(report)

        logger.info("Generated daily report for project %s", project_id)
        return report

    async def send_report_notification(
        self, report: DailyReport, db: AsyncSession
    ) -> None:
        from vibehouse.integrations.sendgrid import EmailClient

        result = await db.execute(
            select(Project).where(Project.id == report.project_id)
        )
        project = result.scalar_one_or_none()
        if not project or not project.owner:
            return

        email_client = EmailClient()
        await email_client.send_email(
            to=project.owner.email,
            subject=f"Daily Build Report: {project.title} - {report.report_date}",
            html_body=f"<h2>Daily Build Report</h2><p>{report.summary}</p>",
        )

        report.sent_at = datetime.now(timezone.utc)
        await db.flush()

        logger.info("Sent daily report notification for project %s", report.project_id)

    async def get_budget_summary(self, project_id: str, db: AsyncSession) -> dict:
        result = await db.execute(
            select(Project).where(Project.id == uuid.UUID(project_id))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        summary = await get_budget_summary(project, db)
        return summary.model_dump(mode="json")
