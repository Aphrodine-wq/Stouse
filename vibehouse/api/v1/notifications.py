import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel as PydanticModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.api.deps import get_current_user, get_db
from vibehouse.db.models.notification import Notification
from vibehouse.db.models.user import User

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# ---------- Schemas ----------


class NotificationResponse(PydanticModel):
    id: uuid.UUID
    type: str
    title: str
    message: str
    is_read: bool
    action_url: str | None
    channel: str
    project_id: uuid.UUID | None
    created_at: str
    model_config = {"from_attributes": True}


class NotificationListResponse(PydanticModel):
    notifications: list[NotificationResponse]
    unread_count: int
    total: int


# ---------- Endpoints ----------


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.is_deleted.is_(False),
    )
    if unread_only:
        query = query.where(Notification.is_read.is_(False))
    query = query.order_by(Notification.created_at.desc()).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    # Count unread
    unread_q = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.is_deleted.is_(False),
        Notification.is_read.is_(False),
    )
    unread_result = await db.execute(unread_q)
    unread_count = len(unread_result.scalars().all())

    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=n.id, type=n.type, title=n.title, message=n.message,
                is_read=n.is_read, action_url=n.action_url, channel=n.channel,
                project_id=n.project_id, created_at=n.created_at.isoformat(),
            )
            for n in notifications
        ],
        unread_count=unread_count,
        total=len(notifications),
    )


@router.post("/{notification_id}/read", status_code=204)
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
    notification = result.scalar_one_or_none()
    if notification:
        notification.is_read = True
        await db.flush()


@router.post("/read-all", status_code=204)
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


@router.get("/count")
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_deleted.is_(False),
            Notification.is_read.is_(False),
        )
    )
    count = len(result.scalars().all())
    return {"unread_count": count}
