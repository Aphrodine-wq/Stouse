import pytest


@pytest.mark.asyncio
async def test_project_timeline(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Timeline Test"},
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/projects/{project_id}/timeline",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert data["project_title"] == "Timeline Test"
    assert "phases" in data
    assert "milestones" in data
    assert "critical_path" in data


@pytest.mark.asyncio
async def test_project_milestones(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Milestone Test"},
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/projects/{project_id}/timeline/milestones",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert "milestones" in data


@pytest.mark.asyncio
async def test_timeline_not_found(client, auth_headers):
    response = await client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/timeline",
        headers=auth_headers,
    )
    assert response.status_code == 404
