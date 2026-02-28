"""WebSocket manager for real-time project updates."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from vibehouse.common.logging import get_logger

logger = get_logger("ws.manager")


class ConnectionManager:
    """Manages WebSocket connections grouped by project ID."""

    def __init__(self):
        self._connections: dict[str, dict[str, WebSocket]] = {}  # project_id -> {conn_id: ws}

    async def connect(self, project_id: str, websocket: WebSocket) -> str:
        await websocket.accept()
        conn_id = uuid.uuid4().hex[:12]
        if project_id not in self._connections:
            self._connections[project_id] = {}
        self._connections[project_id][conn_id] = websocket
        logger.info("WS connected: project=%s conn=%s (%d total)", project_id, conn_id, len(self._connections[project_id]))
        return conn_id

    def disconnect(self, project_id: str, conn_id: str):
        if project_id in self._connections:
            self._connections[project_id].pop(conn_id, None)
            if not self._connections[project_id]:
                del self._connections[project_id]
        logger.info("WS disconnected: project=%s conn=%s", project_id, conn_id)

    async def broadcast(self, project_id: str, event: str, data: dict):
        message = json.dumps({
            "event": event,
            "data": data,
            "project_id": project_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if project_id not in self._connections:
            return
        dead = []
        for conn_id, ws in self._connections[project_id].items():
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(message)
            except Exception:
                dead.append(conn_id)
        for conn_id in dead:
            self.disconnect(project_id, conn_id)

    async def send_personal(self, project_id: str, conn_id: str, event: str, data: dict):
        message = json.dumps({
            "event": event,
            "data": data,
            "project_id": project_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if project_id in self._connections and conn_id in self._connections[project_id]:
            ws = self._connections[project_id][conn_id]
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(message)
            except Exception:
                self.disconnect(project_id, conn_id)

    @property
    def active_connections(self) -> int:
        return sum(len(conns) for conns in self._connections.values())


# Global singleton
manager = ConnectionManager()
