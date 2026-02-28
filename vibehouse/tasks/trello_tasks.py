import asyncio

from vibehouse.common.logging import get_logger
from vibehouse.tasks.celery_app import app

logger = get_logger("tasks.trello")


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(name="vibehouse.tasks.trello_tasks.create_project_board", bind=True, max_retries=3)
def create_project_board(self, project_id: str):
    logger.info("Creating Trello board for project %s", project_id)

    async def _create():
        from vibehouse.core.trello_sync.service import TrelloSyncService
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            try:
                service = TrelloSyncService()
                board_data = await service.create_build_board(project_id, db)
                await db.commit()
                logger.info("Board created for project %s: %s", project_id, board_data["board_id"])
                return board_data
            except Exception as e:
                await db.rollback()
                logger.error("Failed to create board for project %s: %s", project_id, e)
                raise

    try:
        return _run_async(_create())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@app.task(name="vibehouse.tasks.trello_tasks.process_trello_webhook")
def process_trello_webhook(payload: dict):
    logger.info("Processing Trello webhook event")

    async def _process():
        from vibehouse.core.trello_sync.service import TrelloSyncService
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            try:
                service = TrelloSyncService()
                await service.process_webhook(payload, db)
                await db.commit()
            except Exception as e:
                await db.rollback()
                logger.error("Failed to process webhook: %s", e)
                raise

    _run_async(_process())


@app.task(name="vibehouse.tasks.trello_tasks.sync_board_state")
def sync_board_state(project_id: str):
    logger.info("Syncing board state for project %s", project_id)

    async def _sync():
        from vibehouse.core.trello_sync.service import TrelloSyncService
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            try:
                service = TrelloSyncService()
                state = await service.sync_board_state(project_id, db)
                await db.commit()
                return state
            except Exception as e:
                await db.rollback()
                logger.error("Failed to sync board for project %s: %s", project_id, e)

    _run_async(_sync())


@app.task(name="vibehouse.tasks.trello_tasks.sync_all_boards")
def sync_all_boards():
    logger.info("Syncing all active Trello boards")

    async def _sync_all():
        from sqlalchemy import select

        from vibehouse.common.enums import ProjectStatus
        from vibehouse.db.models.project import Project
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            result = await db.execute(
                select(Project).where(
                    Project.status == ProjectStatus.IN_PROGRESS.value,
                    Project.trello_board_id.isnot(None),
                    Project.is_deleted.is_(False),
                )
            )
            projects = result.scalars().all()

            for project in projects:
                sync_board_state.delay(str(project.id))

            logger.info("Queued board sync for %d active projects", len(projects))

    _run_async(_sync_all())
