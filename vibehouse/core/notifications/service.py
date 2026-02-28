"""Notification service for creating and dispatching notifications."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from vibehouse.common.logging import get_logger
from vibehouse.db.models.notification import Notification
from vibehouse.integrations.sendgrid import EmailClient
from vibehouse.integrations.twilio_client import SMSClient

logger = get_logger("notifications.service")


async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    notification_type: str,
    title: str,
    message: str,
    project_id: uuid.UUID | None = None,
    action_url: str | None = None,
    channel: str = "in_app",
    metadata: dict[str, Any] | None = None,
    send_email: bool = False,
    email_address: str | None = None,
    send_sms: bool = False,
    phone_number: str | None = None,
) -> Notification:
    """Create an in-app notification and optionally send email/SMS."""

    notification = Notification(
        user_id=user_id,
        project_id=project_id,
        type=notification_type,
        title=title,
        message=message,
        action_url=action_url,
        channel=channel,
        metadata_json=metadata or {},
    )
    db.add(notification)
    await db.flush()
    await db.refresh(notification)

    logger.info("Created notification: type=%s user=%s title='%s'", notification_type, user_id, title)

    # Send email if requested
    if send_email and email_address:
        email_client = EmailClient()
        html_body = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: #007AFF; color: white; padding: 20px; border-radius: 12px 12px 0 0;">
                <h2 style="margin: 0;">VibeHouse</h2>
            </div>
            <div style="padding: 24px; background: #fff; border: 1px solid #e5e5e5; border-top: none; border-radius: 0 0 12px 12px;">
                <h3 style="margin-top: 0;">{title}</h3>
                <p style="color: #666; line-height: 1.6;">{message}</p>
                {'<a href="' + action_url + '" style="display: inline-block; background: #007AFF; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin-top: 16px;">View Details</a>' if action_url else ''}
            </div>
        </div>
        """
        await email_client.send_email(to=email_address, subject=f"VibeHouse: {title}", html_body=html_body)

    # Send SMS if requested
    if send_sms and phone_number:
        sms_client = SMSClient()
        sms_body = f"VibeHouse: {title} - {message}"
        if len(sms_body) > 160:
            sms_body = sms_body[:157] + "..."
        await sms_client.send_sms(to=phone_number, body=sms_body)

    # Send WebSocket notification
    try:
        from vibehouse.api.v1.ws import notify_user
        await notify_user(str(user_id), notification_type, {
            "id": str(notification.id),
            "title": title,
            "message": message,
            "action_url": action_url,
        })
    except Exception as e:
        logger.debug("WebSocket notification skipped: %s", e)

    return notification
