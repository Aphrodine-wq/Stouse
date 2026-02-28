from pydantic import BaseModel


class BoardConfig(BaseModel):
    name: str
    description: str
    lists: list[str] = [
        "Backlog",
        "This Week",
        "In Progress",
        "Blocked",
        "In Review",
        "Dispute/Hold",
        "Completed",
        "Change Orders",
    ]
    labels: list[dict] = [
        {"name": "Critical Path", "color": "red"},
        {"name": "Inspection Required", "color": "orange"},
        {"name": "Owner Decision", "color": "yellow"},
        {"name": "Change Order", "color": "purple"},
        {"name": "Blocked", "color": "black"},
    ]


class CardData(BaseModel):
    name: str
    description: str | None = None
    list_name: str = "Backlog"
    due_date: str | None = None
    labels: list[str] | None = None
    checklist_items: list[str] | None = None


class WebhookEvent(BaseModel):
    action_type: str
    card_id: str | None = None
    board_id: str | None = None
    list_before: str | None = None
    list_after: str | None = None
    data: dict = {}
