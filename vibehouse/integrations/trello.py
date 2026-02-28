"""Mock Trello integration client.

Returns realistic fake board / list / card data without making any real
API calls.  All IDs are generated with ``uuid4()`` so they are unique
across test runs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from vibehouse.integrations.base import BaseIntegration

# The standard set of lists every VibeHouse project board gets.
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


def _id() -> str:
    """Return a short, Trello-style hex ID."""
    return uuid.uuid4().hex[:24]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TrelloClient(BaseIntegration):
    """Mock Trello integration that returns realistic fake data."""

    BASE_URL = "https://trello.com"

    def __init__(self) -> None:
        super().__init__("trello")

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        self.logger.info("Trello health check: OK (mock)")
        return True

    # ------------------------------------------------------------------
    # Boards
    # ------------------------------------------------------------------

    async def create_board(self, name: str, description: str = "") -> dict[str, Any]:
        """Create a new board and return its metadata dict."""
        board_id = _id()
        short_link = uuid.uuid4().hex[:8]
        board: dict[str, Any] = {
            "id": board_id,
            "name": name,
            "description": description,
            "url": f"{self.BASE_URL}/b/{short_link}/{name.lower().replace(' ', '-')}",
            "shortUrl": f"{self.BASE_URL}/b/{short_link}",
            "closed": False,
            "dateLastActivity": _now_iso(),
            "lists": [],
        }

        # Auto-create the standard lists for the board.
        for idx, list_name in enumerate(STANDARD_BOARD_LISTS):
            list_obj = await self._make_list(board_id, list_name, pos=idx)
            board["lists"].append(list_obj)

        self.logger.info(
            "Created mock board '%s' (id=%s) with %d lists",
            name,
            board_id,
            len(board["lists"]),
        )
        return board

    async def get_board(self, board_id: str) -> dict[str, Any]:
        """Return a mock representation of an existing board."""
        short_link = uuid.uuid4().hex[:8]
        board: dict[str, Any] = {
            "id": board_id,
            "name": "Mock Project Board",
            "description": "Auto-generated mock board for VibeHouse",
            "url": f"{self.BASE_URL}/b/{short_link}/mock-project-board",
            "shortUrl": f"{self.BASE_URL}/b/{short_link}",
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
        """Create a new list on a board."""
        list_obj = await self._make_list(board_id, name)
        self.logger.info(
            "Created mock list '%s' on board %s (id=%s)",
            name,
            board_id,
            list_obj["id"],
        )
        return list_obj

    async def _make_list(
        self, board_id: str, name: str, pos: int = 0
    ) -> dict[str, Any]:
        return {
            "id": _id(),
            "name": name,
            "idBoard": board_id,
            "closed": False,
            "pos": pos * 16384,
        }

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------

    async def create_card(
        self,
        list_id: str,
        name: str,
        description: str = "",
        due_date: str | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a card in a given list."""
        card_id = _id()
        short_link = uuid.uuid4().hex[:8]
        card: dict[str, Any] = {
            "id": card_id,
            "name": name,
            "desc": description,
            "idList": list_id,
            "due": due_date,
            "labels": [
                {"id": _id(), "name": lbl, "color": "blue"}
                for lbl in (labels or [])
            ],
            "url": f"{self.BASE_URL}/c/{short_link}/{name.lower().replace(' ', '-')}",
            "shortUrl": f"{self.BASE_URL}/c/{short_link}",
            "closed": False,
            "dateLastActivity": _now_iso(),
            "checklists": [],
            "comments": [],
        }
        self.logger.info(
            "Created mock card '%s' in list %s (id=%s)", name, list_id, card_id
        )
        return card

    async def move_card(self, card_id: str, list_id: str) -> dict[str, Any]:
        """Move a card to a different list."""
        result: dict[str, Any] = {
            "id": card_id,
            "idList": list_id,
            "dateLastActivity": _now_iso(),
            "moved": True,
        }
        self.logger.info("Moved mock card %s -> list %s", card_id, list_id)
        return result

    # ------------------------------------------------------------------
    # Comments
    # ------------------------------------------------------------------

    async def add_comment(self, card_id: str, text: str) -> dict[str, Any]:
        """Add a comment to a card."""
        comment: dict[str, Any] = {
            "id": _id(),
            "idCard": card_id,
            "type": "commentCard",
            "data": {"text": text},
            "date": _now_iso(),
            "memberCreator": {
                "id": _id(),
                "username": "vibehouse_bot",
                "fullName": "VibeHouse Bot",
            },
        }
        self.logger.info(
            "Added mock comment on card %s (%d chars)", card_id, len(text)
        )
        return comment

    # ------------------------------------------------------------------
    # Checklists
    # ------------------------------------------------------------------

    async def add_checklist(
        self, card_id: str, name: str, items: list[str]
    ) -> dict[str, Any]:
        """Add a checklist with pre-defined items to a card."""
        checklist_id = _id()
        check_items = [
            {
                "id": _id(),
                "name": item,
                "state": "incomplete",
                "pos": idx * 16384,
            }
            for idx, item in enumerate(items)
        ]
        checklist: dict[str, Any] = {
            "id": checklist_id,
            "name": name,
            "idCard": card_id,
            "checkItems": check_items,
        }
        self.logger.info(
            "Added mock checklist '%s' with %d items on card %s",
            name,
            len(items),
            card_id,
        )
        return checklist
