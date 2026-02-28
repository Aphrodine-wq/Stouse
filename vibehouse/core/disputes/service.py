import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.common.enums import DisputeStatus
from vibehouse.common.logging import get_logger
from vibehouse.core.disputes.workflow import (
    check_escalation_needed,
    generate_resolution_options,
)
from vibehouse.db.models.dispute import Dispute

logger = get_logger("disputes.service")


class DisputeService:
    async def generate_options(self, dispute_id: str, db: AsyncSession) -> None:
        result = await db.execute(
            select(Dispute).where(Dispute.id == uuid.UUID(dispute_id))
        )
        dispute = result.scalar_one_or_none()
        if not dispute:
            logger.error("Dispute %s not found", dispute_id)
            return

        analysis = generate_resolution_options(dispute.dispute_type, dispute.description)

        dispute.resolution_options = [opt.model_dump() for opt in analysis.resolution_options]

        history = dispute.history or []
        history.append({
            "action": "ai_analysis",
            "severity": analysis.severity,
            "recommended": analysis.recommended_action,
            "options_count": len(analysis.resolution_options),
        })
        dispute.history = history

        await db.flush()
        logger.info("Generated %d resolution options for dispute %s", len(analysis.resolution_options), dispute_id)

    async def check_escalations(self, db: AsyncSession) -> list[str]:
        active_statuses = [
            DisputeStatus.IDENTIFIED.value,
            DisputeStatus.DIRECT_RESOLUTION.value,
            DisputeStatus.AI_MEDIATION.value,
        ]

        result = await db.execute(
            select(Dispute).where(
                Dispute.status.in_(active_statuses),
                Dispute.is_deleted.is_(False),
            )
        )
        disputes = result.scalars().all()

        escalated = []
        for dispute in disputes:
            # Use escalated_at or updated_at as the status change timestamp
            status_changed_at = dispute.escalated_at or dispute.updated_at

            rule = check_escalation_needed(dispute.status, status_changed_at)
            if rule:
                old_status = dispute.status
                dispute.status = rule.to_status
                dispute.escalated_at = datetime.now(timezone.utc)

                history = dispute.history or []
                history.append({
                    "action": "auto_escalated",
                    "from": old_status,
                    "to": rule.to_status,
                    "reason": rule.notification_message,
                })
                dispute.history = history

                escalated.append(str(dispute.id))
                logger.info(
                    "Auto-escalated dispute %s: %s -> %s",
                    dispute.id,
                    old_status,
                    rule.to_status,
                )

        if escalated:
            await db.flush()

        return escalated

    async def detect_potential_disputes(self, project_id: str, db: AsyncSession) -> list[dict]:
        """Proactive dispute detection based on project state."""
        from vibehouse.common.enums import TaskStatus
        from vibehouse.db.models.phase import ProjectPhase
        from vibehouse.db.models.task import Task

        # Check for blocked tasks
        result = await db.execute(
            select(Task)
            .join(ProjectPhase)
            .where(
                ProjectPhase.project_id == uuid.UUID(project_id),
                Task.status == TaskStatus.BLOCKED.value,
                Task.is_deleted.is_(False),
            )
        )
        blocked_tasks = result.scalars().all()

        alerts = []
        for task in blocked_tasks:
            alerts.append({
                "type": "blocked_task",
                "severity": "medium",
                "message": f"Task '{task.title}' has been blocked",
                "task_id": str(task.id),
            })

        if alerts:
            logger.info(
                "Detected %d potential dispute triggers for project %s",
                len(alerts),
                project_id,
            )

        return alerts
