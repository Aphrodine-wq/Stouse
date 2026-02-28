import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.common.logging import get_logger
from vibehouse.core.orchestration.discovery import discover_vendors
from vibehouse.core.orchestration.outreach import OutreachManager
from vibehouse.core.orchestration.schemas import RFQPackage, VendorMatch, VendorSearchCriteria
from vibehouse.db.models.project import Project
from vibehouse.db.models.vendor import Vendor

logger = get_logger("orchestration.service")


class VendorOrchestrationService:
    def __init__(self):
        self.outreach = OutreachManager()

    async def discover_vendors_for_project(
        self, project_id: str, trade: str, radius_miles: int, db: AsyncSession
    ) -> list[VendorMatch]:
        result = await db.execute(
            select(Project).where(Project.id == uuid.UUID(project_id))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        criteria = VendorSearchCriteria(
            trade=trade,
            location_lat=project.location_lat,
            location_lng=project.location_lng,
            radius_miles=radius_miles,
        )

        matches = await discover_vendors(criteria, db)

        logger.info(
            "Discovered %d vendors for project %s, trade: %s",
            len(matches),
            project_id,
            trade,
        )
        return matches

    async def send_rfqs(
        self, project_id: str, vendor_ids: list[str], trade: str, db: AsyncSession
    ) -> list[dict]:
        result = await db.execute(
            select(Project).where(Project.id == uuid.UUID(project_id))
        )
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found")

        results = []
        for vid in vendor_ids:
            vendor_result = await db.execute(
                select(Vendor).where(Vendor.id == uuid.UUID(vid))
            )
            vendor = vendor_result.scalar_one_or_none()
            if not vendor:
                continue

            rfq = RFQPackage(
                project_title=project.title,
                project_address=project.address,
                scope_description=f"{trade} work for {project.title}",
                required_trade=trade,
                budget_range=f"${project.budget:,.0f}" if project.budget else None,
            )

            email_result = await self.outreach.send_rfq_email(
                vendor_email=vendor.email,
                vendor_name=vendor.contact_name or vendor.company_name,
                rfq=rfq,
            )

            if vendor.phone:
                await self.outreach.send_rfq_sms(vendor_phone=vendor.phone, rfq=rfq)

            results.append({
                "vendor_id": vid,
                "vendor_name": vendor.company_name,
                "email_sent": True,
                "sms_sent": bool(vendor.phone),
            })

        logger.info("Sent RFQs to %d vendors for project %s", len(results), project_id)
        return results
