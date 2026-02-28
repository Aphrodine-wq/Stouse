import uuid

import pytest

from vibehouse.db.models.notification import Notification


@pytest.mark.asyncio
async def test_list_notifications_empty(client, auth_headers):
    response = await client.get(
        "/api/v1/notifications",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 0
    assert "unread_count" in data


@pytest.mark.asyncio
async def test_mark_notification_read(client, auth_headers, homeowner_user, db_session):
    # Create a notification directly in the DB
    notif = Notification(
        id=uuid.uuid4(),
        user_id=homeowner_user.id,
        channel="in_app",
        category="task_update",
        title="Task completed",
        body="Framing inspection passed",
        is_read=False,
    )
    db_session.add(notif)
    await db_session.flush()
    await db_session.refresh(notif)

    response = await client.post(
        f"/api/v1/notifications/{notif.id}/read",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True


@pytest.mark.asyncio
async def test_mark_all_read(client, auth_headers, homeowner_user, db_session):
    # Create a couple of unread notifications
    for i in range(3):
        notif = Notification(
            id=uuid.uuid4(),
            user_id=homeowner_user.id,
            channel="in_app",
            category="report",
            title=f"Daily report #{i}",
            body="Your daily report is ready",
            is_read=False,
        )
        db_session.add(notif)
    await db_session.flush()

    response = await client.post(
        "/api/v1/notifications/read-all",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "All notifications marked as read"


@pytest.mark.asyncio
async def test_get_notification_preferences(client, auth_headers):
    response = await client.get(
        "/api/v1/notifications/preferences",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "email_enabled" in data
    assert "sms_enabled" in data
    assert "categories" in data


@pytest.mark.asyncio
async def test_update_notification_preferences(client, auth_headers):
    response = await client.put(
        "/api/v1/notifications/preferences",
        headers=auth_headers,
        json={
            "email_enabled": True,
            "sms_enabled": True,
            "in_app_enabled": True,
            "categories": {
                "task_update": True,
                "dispute": True,
                "report": False,
                "budget_alert": True,
                "change_order": True,
                "invitation": True,
                "photo": True,
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sms_enabled"] is True
    assert data["categories"]["photo"] is True
