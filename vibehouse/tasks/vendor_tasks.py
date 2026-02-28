import asyncio

from vibehouse.common.logging import get_logger
from vibehouse.tasks.celery_app import app

logger = get_logger("tasks.vendor")


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@app.task(name="vibehouse.tasks.vendor_tasks.discover_vendors_for_project")
def discover_vendors_for_project(project_id: str, trade: str, radius_miles: int = 50):
    logger.info("Discovering vendors for project %s, trade: %s", project_id, trade)

    async def _discover():
        from vibehouse.core.orchestration.service import VendorOrchestrationService
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            try:
                service = VendorOrchestrationService()
                matches = await service.discover_vendors_for_project(
                    project_id, trade, radius_miles, db
                )
                await db.commit()

                # Auto-send RFQs to top matches
                if matches:
                    top_vendor_ids = [m.vendor_id for m in matches[:5]]
                    send_vendor_rfqs.delay(project_id, top_vendor_ids, trade)

                logger.info("Found %d vendors for project %s", len(matches), project_id)
                return [m.model_dump() for m in matches]
            except Exception as e:
                await db.rollback()
                logger.error("Vendor discovery failed for project %s: %s", project_id, e)
                raise

    return _run_async(_discover())


@app.task(name="vibehouse.tasks.vendor_tasks.send_vendor_rfqs")
def send_vendor_rfqs(project_id: str, vendor_ids: list[str], trade: str):
    logger.info("Sending RFQs to %d vendors for project %s", len(vendor_ids), project_id)

    async def _send():
        from vibehouse.core.orchestration.service import VendorOrchestrationService
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            try:
                service = VendorOrchestrationService()
                results = await service.send_rfqs(project_id, vendor_ids, trade, db)
                await db.commit()
                logger.info("Sent RFQs to %d vendors", len(results))
                return results
            except Exception as e:
                await db.rollback()
                logger.error("RFQ sending failed for project %s: %s", project_id, e)
                raise

    return _run_async(_send())


@app.task(name="vibehouse.tasks.vendor_tasks.send_rfq_followup")
def send_rfq_followup(project_id: str, vendor_ids: list[str]):
    logger.info("Sending RFQ followups for project %s", project_id)

    async def _followup():
        from sqlalchemy import select

        from vibehouse.core.orchestration.outreach import OutreachManager
        from vibehouse.db.models.project import Project
        from vibehouse.db.models.vendor import Vendor
        from vibehouse.db.session import async_session_factory

        async with async_session_factory() as db:
            import uuid as _uuid

            result = await db.execute(
                select(Project).where(Project.id == _uuid.UUID(project_id))
            )
            project = result.scalar_one_or_none()
            if not project:
                return

            outreach = OutreachManager()
            for vid in vendor_ids:
                v_result = await db.execute(
                    select(Vendor).where(Vendor.id == _uuid.UUID(vid))
                )
                vendor = v_result.scalar_one_or_none()
                if vendor:
                    await outreach.send_followup(
                        vendor.email,
                        vendor.contact_name or vendor.company_name,
                        project.title,
                    )

    _run_async(_followup())
