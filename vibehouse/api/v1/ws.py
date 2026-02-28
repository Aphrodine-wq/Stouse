"""WebSocket endpoint for real-time notifications."""

from __future__ import annotations

import json
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from vibehouse.common.logging import get_logger
from vibehouse.common.security import decode_token

router = APIRouter(tags=["WebSocket"])

logger = get_logger("ws")

# In-memory connection manager (in production, back this with Redis pub/sub)
_connections: dict[str, list[WebSocket]] = defaultdict(list)


class ConnectionManager:
    """Manages WebSocket connections per user."""

    def __init__(self) -> None:
        self.active: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.active[user_id].append(ws)
        logger.info("WebSocket connected: user=%s (total=%d)", user_id, len(self.active[user_id]))

    def disconnect(self, user_id: str, ws: WebSocket) -> None:
        if ws in self.active[user_id]:
            self.active[user_id].remove(ws)
        if not self.active[user_id]:
            del self.active[user_id]
        logger.info("WebSocket disconnected: user=%s", user_id)

    async def send_to_user(self, user_id: str, message: dict) -> None:
        if user_id in self.active:
            dead = []
            for ws in self.active[user_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.active[user_id].remove(ws)

    async def broadcast(self, message: dict) -> None:
        for user_id in list(self.active.keys()):
            await self.send_to_user(user_id, message)

    @property
    def connected_users(self) -> int:
        return len(self.active)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Authenticate via token query param, then stream notifications."""
    token = ws.query_params.get("token", "")
    try:
        payload = decode_token(token)
        user_id = payload.get("sub", "")
        if not user_id or payload.get("type") != "access":
            await ws.close(code=4001, reason="Invalid token")
            return
    except Exception:
        await ws.close(code=4001, reason="Invalid token")
        return

    await manager.connect(user_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            # Handle ping/pong
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(user_id, ws)


async def notify_user(user_id: str, notification_type: str, data: dict) -> None:
    """Send a real-time notification to a user via WebSocket."""
    await manager.send_to_user(user_id, {
        "type": "notification",
        "notification_type": notification_type,
        "data": data,
    })
