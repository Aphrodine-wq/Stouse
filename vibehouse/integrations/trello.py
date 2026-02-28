"""Trello integration client.

Uses real Trello REST API when valid keys are configured, otherwise
falls back to mock responses for development.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from vibehouse.config import settings
from vibehouse.integrations.base import BaseIntegration

STANDARD_BOARD_LISTS: list[str] = [
    "Backlog",
    "This Week",
    "In Progress",
    "Blocked",
    "In Review",
    "Dispute/Hold",
    "Completed",
    "Change Orders",
]


def _is_mock() -> bool:
    return settings.TRELLO_API_KEY.startswith("mock_")


def _id() -> str:
    return uuid.uuid4().hex[:24]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TrelloClient(BaseIntegration):
    """Trello integration with real API support and mock fallback."""

    API_URL = "https://api.trello.com/1"
    WEB_URL = "https://trello.com"

    def __init__(self) -> None:
        super().__init__("trello")

    def _params(self) -> dict[str, str]:
        return {"key": settings.TRELLO_API_KEY, "token": settings.TRELLO_API_SECRET}

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        params = {**self._params(), **kwargs.pop("params", {})}
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(method, f"{self.API_URL}{path}", params=params, **kwargs)
            resp.raise_for_status()
            return resp.json()

    async def health_check(self) -> bool:
        if _is_mock():
            self.logger.info("Trello health check: OK (mock)")
            return True
        try:
            await self._request("GET", "/members/me")
            return True
        except Exception as e:
            self.logger.error("Trello health check failed: %s", e)
            return False

    # ------------------------------------------------------------------
    # Boards
    # ------------------------------------------------------------------

    async def create_board(self, name: str, description: str = "") -> dict[str, Any]:
        if not _is_mock():
            self.logger.info("Creating real Trello board: %s", name)
            board = await self._request(
                "POST", "/boards",
                json={"name": name, "desc": description, "defaultLists": "false"},
            )
            lists = []
            for idx, list_name in enumerate(STANDARD_BOARD_LISTS):
                lst = await self._request(
                    "POST", "/lists",
                    json={"name": list_name, "idBoard": board["id"], "pos": idx * 16384},
                )
                lists.append(lst)
            board["lists"] = lists
            self.logger.info("Created board '%s' (id=%s) with %d lists", name, board["id"], len(lists))
            return board

        board_id = _id()
        short_link = uuid.uuid4().hex[:8]
        board: dict[str, Any] = {
            "id": board_id,
            "name": name,
            "description": description,
            "url": f"{self.WEB_URL}/b/{short_link}/{name.lower().replace(' ', '-')}",
            "shortUrl": f"{self.WEB_URL}/b/{short_link}",
            "closed": False,
            "dateLastActivity": _now_iso(),
            "lists": [],
        }
        for idx, list_name in enumerate(STANDARD_BOARD_LISTS):
            list_obj = await self._make_list(board_id, list_name, pos=idx)
            board["lists"].append(list_obj)
        self.logger.info("Created mock board '%s' (id=%s)", name, board_id)
        return board

    async def get_board(self, board_id: str) -> dict[str, Any]:
        if not _is_mock():
            board = await self._request("GET", f"/boards/{board_id}", params={"lists": "all"})
            self.logger.info("Fetched board (id=%s)", board_id)
            return board

        short_link = uuid.uuid4().hex[:8]
        board: dict[str, Any] = {
            "id": board_id,
            "name": "Mock Project Board",
            "description": "Auto-generated mock board",
            "url": f"{self.WEB_URL}/b/{short_link}/mock-project-board",
            "shortUrl": f"{self.WEB_URL}/b/{short_link}",
            "closed": False,
            "dateLastActivity": _now_iso(),
            "lists": [],
        }
        for idx, list_name in enumerate(STANDARD_BOARD_LISTS):
            list_obj = await self._make_list(board_id, list_name, pos=idx)
            board["lists"].append(list_obj)
        self.logger.info("Fetched mock board (id=%s)", board_id)
        return board

    # ------------------------------------------------------------------
    # Lists
    # ------------------------------------------------------------------

    async def create_list(self, board_id: str, name: str) -> dict[str, Any]:
        if not _is_mock():
            lst = await self._request("POST", "/lists", json={"name": name, "idBoard": board_id})
            self.logger.info("Created list '%s' on board %s", name, board_id)
            return lst

        list_obj = await self._make_list(board_id, name)
        self.logger.info("Created mock list '%s' on board %s", name, board_id)
        return list_obj

    async def _make_list(self, board_id: str, name: str, pos: int = 0) -> dict[str, Any]:
        return {"id": _id(), "name": name, "idBoard": board_id, "closed": False, "pos": pos * 16384}

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------

    async def create_card(
        self, list_id: str, name: str, description: str = "",
        due_date: str | None = None, labels: list[str] | None = None,
    ) -> dict[str, Any]:
        if not _is_mock():
            payload: dict[str, Any] = {"name": name, "desc": description, "idList": list_id}
            if due_date:
                payload["due"] = due_date
            card = await self._request("POST", "/cards", json=payload)
            self.logger.info("Created card '%s' (id=%s)", name, card["id"])
            return card

        card_id = _id()
        short_link = uuid.uuid4().hex[:8]
        card: dict[str, Any] = {
            "id": card_id, "name": name, "desc": description, "idList": list_id,
            "due": due_date,
            "labels": [{"id": _id(), "name": lbl, "color": "blue"} for lbl in (labels or [])],
            "url": f"{self.WEB_URL}/c/{short_link}/{name.lower().replace(' ', '-')}",
            "shortUrl": f"{self.WEB_URL}/c/{short_link}",
            "closed": False, "dateLastActivity": _now_iso(), "checklists": [], "comments": [],
        }
        self.logger.info("Created mock card '%s' (id=%s)", name, card_id)
        return card

    async def move_card(self, card_id: str, list_id: str) -> dict[str, Any]:
        if not _is_mock():
            card = await self._request("PUT", f"/cards/{card_id}", json={"idList": list_id})
            self.logger.info("Moved card %s -> list %s", card_id, list_id)
            return card

        result: dict[str, Any] = {"id": card_id, "idList": list_id, "dateLastActivity": _now_iso(), "moved": True}
        self.logger.info("Moved mock card %s -> list %s", card_id, list_id)
        return result

    # ------------------------------------------------------------------
    # Comments & Checklists
    # ------------------------------------------------------------------

    async def add_comment(self, card_id: str, text: str) -> dict[str, Any]:
        if not _is_mock():
            comment = await self._request("POST", f"/cards/{card_id}/actions/comments", json={"text": text})
            self.logger.info("Added comment on card %s", card_id)
            return comment

        comment: dict[str, Any] = {
            "id": _id(), "idCard": card_id, "type": "commentCard",
            "data": {"text": text}, "date": _now_iso(),
            "memberCreator": {"id": _id(), "username": "vibehouse_bot", "fullName": "VibeHouse Bot"},
        }
        self.logger.info("Added mock comment on card %s", card_id)
        return comment

    async def add_checklist(self, card_id: str, name: str, items: list[str]) -> dict[str, Any]:
        if not _is_mock():
            checklist = await self._request("POST", f"/cards/{card_id}/checklists", json={"name": name})
            for item in items:
                await self._request("POST", f"/checklists/{checklist['id']}/checkItems", json={"name": item})
            self.logger.info("Added checklist '%s' with %d items", name, len(items))
            return checklist

        checklist_id = _id()
        check_items = [
            {"id": _id(), "name": item, "state": "incomplete", "pos": idx * 16384}
            for idx, item in enumerate(items)
        ]
        checklist: dict[str, Any] = {"id": checklist_id, "name": name, "idCard": card_id, "checkItems": check_items}
        self.logger.info("Added mock checklist '%s' with %d items", name, len(items))
        return checklist

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    async def create_webhook(self, callback_url: str, model_id: str) -> dict[str, Any]:
        if not _is_mock():
            webhook = await self._request(
                "POST", "/webhooks", json={"callbackURL": callback_url, "idModel": model_id},
            )
            self.logger.info("Created webhook for model %s", model_id)
            return webhook

        return {"id": _id(), "callbackURL": callback_url, "idModel": model_id, "active": True}
