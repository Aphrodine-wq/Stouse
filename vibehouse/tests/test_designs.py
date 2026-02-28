import pytest


@pytest.mark.asyncio
async def test_submit_vibe(client, auth_headers):
    # Create project
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Vibe Test House"},
    )
    project_id = create_resp.json()["id"]

    # Submit vibe
    response = await client.post(
        f"/api/v1/projects/{project_id}/vibe",
        headers=auth_headers,
        json={"vibe_description": "Modern 3 bedroom house with pool and garage"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "designing"
    assert data["project_id"] == project_id


@pytest.mark.asyncio
async def test_list_designs_empty(client, auth_headers):
    # Create project
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Empty Designs"},
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/projects/{project_id}/designs",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_submit_vibe_wrong_status(client, auth_headers):
    # Create project and transition to planning
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Wrong Status"},
    )
    project_id = create_resp.json()["id"]

    # Transition: draft -> designing -> planning
    await client.patch(
        f"/api/v1/projects/{project_id}",
        headers=auth_headers,
        json={"status": "designing"},
    )
    await client.patch(
        f"/api/v1/projects/{project_id}",
        headers=auth_headers,
        json={"status": "planning"},
    )

    # Try to submit vibe in planning status
    response = await client.post(
        f"/api/v1/projects/{project_id}/vibe",
        headers=auth_headers,
        json={"vibe_description": "Should fail"},
    )
    assert response.status_code == 400
