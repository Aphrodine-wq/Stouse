"""Notification management and delivery preferences."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db
from vibehouse.common.pagination import PaginatedResponse, PaginationParams, paginate
from vibehouse.db.models.notification import Notification
from vibehouse.db.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ---------- Schemas ----------

class NotificationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID | None
    channel: str
    category: str
    title: str
    body: str
    is_read: bool
    action_url: str | None
    created_at: str
    model_config = {"from_attributes": True}


class NotificationListResponse(PaginatedResponse[NotificationResponse]):
    unread_count: int


class NotificationPreferences(BaseModel):
    email_enabled: bool = True
    sms_enabled: bool = False
    in_app_enabled: bool = True
    categories: dict[str, bool] = {
        "task_update": True,
        "dispute": True,
        "report": True,
        "budget_alert": True,
        "change_order": True,
        "invitation": True,
        "photo": False,
    }


# ---------- Endpoints ----------

@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    params: PaginationParams = Depends(),
    unread_only: bool = False,
):
    query = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.is_deleted.is_(False),
    )
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    query = query.order_by(Notification.created_at.desc())

    items, total = await paginate(db, query, params, Notification)
    total_pages = (total + params.page_size - 1) // params.page_size

    # Count unread
    unread_q = await db.execute(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
            Notification.is_deleted.is_(False),
        )
    )
    unread_count = len(unread_q.scalars().all())

    return NotificationListResponse(
        items=[_notif_response(n) for n in items],
        total=total, page=params.page, page_size=params.page_size,
        total_pages=total_pages, unread_count=unread_count,
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notif = result.scalar_one_or_none()
    if not notif:
        from vibehouse.common.exceptions import NotFoundError
        raise NotFoundError("Notification", str(notification_id))

    notif.is_read = True
    await db.flush()
    await db.refresh(notif)
    return _notif_response(notif)


@router.post("/read-all")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.flush()
    return {"message": "All notifications marked as read"}


@router.get("/preferences", response_model=NotificationPreferences)
async def get_preferences(current_user: User = Depends(get_current_user)):
    prefs = current_user.preferences or {}
    notif_prefs = prefs.get("notifications", {})
    return NotificationPreferences(**notif_prefs) if notif_prefs else NotificationPreferences()


@router.put("/preferences", response_model=NotificationPreferences)
async def update_preferences(
    body: NotificationPreferences,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = current_user.preferences or {}
    prefs["notifications"] = body.model_dump()
    current_user.preferences = prefs
    await db.flush()
    return body


def _notif_response(n: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=n.id, project_id=n.project_id, channel=n.channel,
        category=n.category, title=n.title, body=n.body,
        is_read=n.is_read, action_url=n.action_url,
        created_at=n.created_at.isoformat(),
    )
