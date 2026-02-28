import asyncio

from vibehouse.common.logging import get_logger
from vibehouse.tasks.celery_app import app

logger = get_logger("tasks.report")


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(name="vibehouse.tasks.report_tasks.generate_daily_report")
def generate_daily_report(project_id: str):
    logger.info("Generating daily report for project %s", project_id)

    async def _generate():
        from vibehouse.core.reporting.service import ReportingService
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            try:
                service = ReportingService()
                report = await service.generate_daily_report(project_id, db)
                await service.send_report_notification(report, db)
                await db.commit()
                logger.info("Daily report generated and sent for project %s", project_id)
                return str(report.id)
            except Exception as e:
                await db.rollback()
                logger.error("Report generation failed for project %s: %s", project_id, e)
                raise

    return _run_async(_generate())


@app.task(name="vibehouse.tasks.report_tasks.generate_all_daily_reports")
def generate_all_daily_reports():
    """Celery Beat task: generate daily reports for all active projects."""
    logger.info("Generating daily reports for all active projects")

    async def _generate_all():
        from sqlalchemy import select

        from vibehouse.common.enums import ProjectStatus
        from vibehouse.db.models.project import Project
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            result = await db.execute(
                select(Project).where(
                    Project.status == ProjectStatus.IN_PROGRESS.value,
                    Project.is_deleted.is_(False),
                )
            )
            projects = result.scalars().all()

            for project in projects:
                generate_daily_report.delay(str(project.id))

            logger.info("Queued daily reports for %d active projects", len(projects))

    _run_async(_generate_all())
