"""Event bus for broadcasting real-time updates to WebSocket clients."""

from __future__ import annotations

import asyncio

from vibehouse.common.logging import get_logger

logger = get_logger("events")


async def emit(project_id: str, event: str, data: dict) -> None:
    """Broadcast an event to all WebSocket connections for a project.

    Safe to call from anywhere – silently no-ops if no clients connected.
    """
    try:
        from vibehouse.api.ws import manager
        await manager.broadcast(project_id, event, data)
    except Exception as e:
        logger.debug("Event emit failed (non-critical): %s", e)


def emit_sync(project_id: str, event: str, data: dict) -> None:
    """Fire-and-forget emit for use from synchronous Celery tasks."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(emit(project_id, event, data))
        else:
            loop.run_until_complete(emit(project_id, event, data))
    except RuntimeError:
        # No running loop (e.g., inside Celery worker) – skip
        pass
