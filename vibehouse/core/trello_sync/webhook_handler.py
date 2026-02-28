from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.common.enums import TaskStatus
from vibehouse.common.logging import get_logger
from vibehouse.db.models.task import Task

logger = get_logger("trello_sync.webhook_handler")

# Mapping Trello list names to internal task statuses
LIST_STATUS_MAP = {
    "Backlog": TaskStatus.BACKLOG,
    "This Week": TaskStatus.SCHEDULED,
    "In Progress": TaskStatus.IN_PROGRESS,
    "Blocked": TaskStatus.BLOCKED,
    "In Review": TaskStatus.IN_REVIEW,
    "Completed": TaskStatus.COMPLETED,
    "Dispute/Hold": TaskStatus.BLOCKED,
    "Change Orders": TaskStatus.IN_REVIEW,
}


async def handle_webhook_event(event: dict, db: AsyncSession) -> None:
    action = event.get("action", {})
    action_type = action.get("type", "")

    handlers = {
        "updateCard": _handle_card_update,
        "commentCard": _handle_card_comment,
        "updateCheckItemStateOnCard": _handle_checklist_update,
    }

    handler = handlers.get(action_type)
    if handler:
        await handler(action, db)
    else:
        logger.debug("Unhandled webhook action type: %s", action_type)


async def _handle_card_update(action: dict, db: AsyncSession) -> None:
    data = action.get("data", {})
    card = data.get("card", {})
    card_id = card.get("id")

    if not card_id:
        return

    # Check if card was moved to a different list
    list_after = data.get("listAfter", {})
    list_before = data.get("listBefore", {})

    if list_after and list_before:
        new_list_name = list_after.get("name", "")
        new_status = LIST_STATUS_MAP.get(new_list_name)

        if new_status:
            result = await db.execute(
                select(Task).where(Task.trello_card_id == card_id)
            )
            task = result.scalar_one_or_none()

            if task:
                old_status = task.status
                task.status = new_status.value
                logger.info(
                    "Task %s moved: %s -> %s (Trello: %s -> %s)",
                    task.id,
                    old_status,
                    new_status.value,
                    list_before.get("name"),
                    new_list_name,
                )


async def _handle_card_comment(action: dict, db: AsyncSession) -> None:
    data = action.get("data", {})
    card = data.get("card", {})
    card_id = card.get("id")
    text = data.get("text", "")

    if not card_id:
        return

    logger.info("Comment on card %s: %s", card_id, text[:100])

    # Check for issue keywords that might trigger dispute detection
    issue_keywords = ["problem", "issue", "delay", "damaged", "wrong", "dispute", "complaint"]
    if any(keyword in text.lower() for keyword in issue_keywords):
        logger.warning("Potential issue detected in card comment: %s", card_id)


async def _handle_checklist_update(action: dict, db: AsyncSession) -> None:
    data = action.get("data", {})
    check_item = data.get("checkItem", {})
    state = check_item.get("state", "")
    card = data.get("card", {})
    card_id = card.get("id")

    if not card_id:
        return

    logger.info("Checklist item %s on card %s: %s", check_item.get("name"), card_id, state)
