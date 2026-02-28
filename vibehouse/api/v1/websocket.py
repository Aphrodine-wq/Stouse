"""WebSocket endpoint for real-time project updates.

Clients connect to /api/v1/ws/projects/{project_id}?token=<jwt>
and receive events like:
  - project.status_changed
  - design.generated
  - task.updated
  - dispute.filed / dispute.escalated / dispute.resolved
  - report.generated
  - board.synced
  - budget.alert
"""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.ws import manager
from vibehouse.common.enums import UserRole
from vibehouse.common.logging import get_logger
from vibehouse.common.security import decode_token
from vibehouse.db.models.project import Project
from vibehouse.db.models.user import User
from vibehouse.db.session import async_session_factory

logger = get_logger("api.v1.websocket")

router = APIRouter(tags=["WebSocket"])


async def _authenticate_ws(token: str) -> User | None:
    try:
        payload = decode_token(token)
    except ValueError:
        return None
    if payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    async with async_session_factory() as db:
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(user_id), User.is_deleted.is_(False))
        )
        return result.scalar_one_or_none()


async def _check_project_access(user: User, project_id: str, db: AsyncSession) -> bool:
    result = await db.execute(
        select(Project).where(Project.id == uuid.UUID(project_id), Project.is_deleted.is_(False))
    )
    project = result.scalar_one_or_none()
    if not project:
        return False
    if user.role == UserRole.ADMIN.value:
        return True
    return project.owner_id == user.id


@router.websocket("/ws/projects/{project_id}")
async def project_websocket(
    websocket: WebSocket,
    project_id: str,
    token: str = Query(...),
):
    # Authenticate
    user = await _authenticate_ws(token)
    if not user:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # Authorize
    async with async_session_factory() as db:
        has_access = await _check_project_access(user, project_id, db)
    if not has_access:
        await websocket.close(code=4003, reason="Access denied")
        return

    conn_id = await manager.connect(project_id, websocket)

    # Send welcome
    await manager.send_personal(project_id, conn_id, "connected", {
        "message": "Connected to project updates",
        "user_id": str(user.id),
        "user_name": user.full_name,
    })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal(project_id, conn_id, "error", {
                    "message": "Invalid JSON"
                })
                continue

            action = msg.get("action")

            if action == "ping":
                await manager.send_personal(project_id, conn_id, "pong", {})

            elif action == "subscribe":
                # Client can subscribe to specific event types
                events = msg.get("events", [])
                await manager.send_personal(project_id, conn_id, "subscribed", {
                    "events": events,
                })

            else:
                await manager.send_personal(project_id, conn_id, "error", {
                    "message": f"Unknown action: {action}"
                })

    except WebSocketDisconnect:
        manager.disconnect(project_id, conn_id)
    except Exception as e:
        logger.error("WebSocket error: %s", e)
        manager.disconnect(project_id, conn_id)
