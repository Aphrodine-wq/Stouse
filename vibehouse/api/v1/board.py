import hashlib
import hmac
import uuid

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db
from vibehouse.common.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from vibehouse.common.enums import UserRole
from vibehouse.config import settings
from vibehouse.db.models.project import Project
from vibehouse.db.models.trello_state import TrelloSyncState
from vibehouse.db.models.user import User

router = APIRouter(tags=["Board"])


# ---------- Schemas ----------


class BoardStateResponse(BaseModel):
    project_id: uuid.UUID
    board_id: str | None
    last_sync: str | None
    sync_status: str
    board_state: dict | None

    model_config = {"from_attributes": True}


class WebhookResponse(BaseModel):
    status: str
    message: str


# ---------- Endpoints ----------


@router.get("/projects/{project_id}/board", response_model=BoardStateResponse)
async def get_board_state(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify project access
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.is_deleted.is_(False))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundError("Project", str(project_id))
    if current_user.role != UserRole.ADMIN.value and project.owner_id != current_user.id:
        raise PermissionDeniedError("You do not have access to this project")

    result = await db.execute(
        select(TrelloSyncState).where(TrelloSyncState.project_id == project_id)
    )
    sync_state = result.scalar_one_or_none()

    if not sync_state:
        return BoardStateResponse(
            project_id=project_id,
            board_id=None,
            last_sync=None,
            sync_status="not_created",
            board_state=None,
        )

    return BoardStateResponse(
        project_id=sync_state.project_id,
        board_id=sync_state.board_id,
        last_sync=sync_state.last_sync.isoformat() if sync_state.last_sync else None,
        sync_status=sync_state.sync_status,
        board_state=sync_state.board_state,
    )


@router.post("/webhooks/trello", response_model=WebhookResponse)
async def trello_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()

    # Trello sends HEAD requests to verify webhook URL
    if request.method == "HEAD":
        return WebhookResponse(status="ok", message="Webhook verified")

    # Validate Trello webhook signature
    signature = request.headers.get("x-trello-webhook")
    if signature and settings.TRELLO_API_SECRET != "mock_trello_secret":
        callback_url = str(request.url)
        computed = hmac.new(
            settings.TRELLO_API_SECRET.encode(),
            body + callback_url.encode(),
            hashlib.sha1,
        ).digest()
        import base64

        expected = base64.b64encode(computed).decode()
        if not hmac.compare_digest(signature, expected):
            raise BadRequestError("Invalid webhook signature")

    # Parse and enqueue webhook processing
    import json

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise BadRequestError("Invalid JSON payload")

    from vibehouse.tasks.trello_tasks import process_trello_webhook

    process_trello_webhook.delay(payload)

    return WebhookResponse(status="accepted", message="Webhook event queued for processing")
