import pytest


@pytest.mark.asyncio
async def test_project_dashboard(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={
            "title": "Dashboard Test",
            "budget": 500000,
            "address": "456 Oak Ave, Austin, TX 78702",
        },
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/projects/{project_id}/dashboard",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()

    # Check all top-level sections exist
    assert "project_summary" in data
    assert "phase_progress" in data
    assert "task_summary" in data
    assert "financial_summary" in data
    assert "timeline" in data
    assert "recent_activity" in data
    assert "active_disputes" in data
    assert "active_change_orders" in data
    assert "pending_decisions" in data

    # Verify project summary
    assert data["project_summary"]["title"] == "Dashboard Test"
    assert data["project_summary"]["budget"] == "500000.00"

    # Financial summary should be healthy with no spend
    assert data["financial_summary"]["total_spent"] == "0.00"
    assert data["financial_summary"]["alert_level"] == "green"


@pytest.mark.asyncio
async def test_dashboard_with_weather(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={
            "title": "Weather Dashboard",
            "address": "789 Pine St, Austin, TX",
        },
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/projects/{project_id}/dashboard",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["weather_note"] is not None


@pytest.mark.asyncio
async def test_dashboard_not_found(client, auth_headers):
    response = await client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/dashboard",
        headers=auth_headers,
    )
    assert response.status_code == 404
