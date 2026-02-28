import asyncio

from vibehouse.common.logging import get_logger
from vibehouse.tasks.celery_app import app

logger = get_logger("tasks.vibe")


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(name="vibehouse.tasks.vibe_tasks.process_vibe_description", bind=True, max_retries=3)
def process_vibe_description(self, project_id: str, vibe_text: str):
    logger.info("Processing vibe description for project %s", project_id)

    async def _process():
        from vibehouse.core.vibe_engine.service import VibeEngineService
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            try:
                service = VibeEngineService()
                artifacts = await service.process_vibe(project_id, vibe_text, db)
                await db.commit()
                logger.info(
                    "Created %d design artifacts for project %s",
                    len(artifacts),
                    project_id,
                )
                return [str(a.id) for a in artifacts]
            except Exception as e:
                await db.rollback()
                logger.error("Failed to process vibe for project %s: %s", project_id, e)
                raise

    try:
        return _run_async(_process())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
