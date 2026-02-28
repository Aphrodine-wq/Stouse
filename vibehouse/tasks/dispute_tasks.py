import asyncio

from vibehouse.common.logging import get_logger
from vibehouse.tasks.celery_app import app

logger = get_logger("tasks.dispute")


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(name="vibehouse.tasks.dispute_tasks.generate_resolution_options")
def generate_resolution_options(dispute_id: str):
    logger.info("Generating resolution options for dispute %s", dispute_id)

    async def _generate():
        from vibehouse.core.disputes.service import DisputeService
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            try:
                service = DisputeService()
                await service.generate_options(dispute_id, db)
                await db.commit()
                logger.info("Resolution options generated for dispute %s", dispute_id)
            except Exception as e:
                await db.rollback()
                logger.error("Failed to generate options for dispute %s: %s", dispute_id, e)
                raise

    _run_async(_generate())


@app.task(name="vibehouse.tasks.dispute_tasks.check_all_escalations")
def check_all_escalations():
    """Celery Beat task: check all active disputes for auto-escalation."""
    logger.info("Checking dispute escalations")

    async def _check():
        from vibehouse.core.disputes.service import DisputeService
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            try:
                service = DisputeService()
                escalated = await service.check_escalations(db)
                await db.commit()

                if escalated:
                    logger.info("Auto-escalated %d disputes", len(escalated))
                return escalated
            except Exception as e:
                await db.rollback()
                logger.error("Escalation check failed: %s", e)
                raise

    return _run_async(_check())


@app.task(name="vibehouse.tasks.dispute_tasks.detect_potential_disputes")
def detect_potential_disputes(project_id: str):
    logger.info("Detecting potential disputes for project %s", project_id)

    async def _detect():
        from vibehouse.core.disputes.service import DisputeService
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            try:
                service = DisputeService()
                alerts = await service.detect_potential_disputes(project_id, db)
                logger.info("Found %d potential dispute triggers for project %s", len(alerts), project_id)
                return alerts
            except Exception as e:
                logger.error("Dispute detection failed for project %s: %s", project_id, e)
                raise

    return _run_async(_detect())
