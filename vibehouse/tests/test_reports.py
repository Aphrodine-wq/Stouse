import pytest


@pytest.mark.asyncio
async def test_list_reports_empty(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Reports Test"},
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/projects/{project_id}/reports/daily",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_get_latest_report_none(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "No Reports"},
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/projects/{project_id}/reports/daily/latest",
        headers=auth_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_budget(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Budget Test", "budget": 400000},
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/projects/{project_id}/budget",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_budget"] == "400000.00"
    assert data["total_spent"] == "0.00"
