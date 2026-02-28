import pytest


@pytest.mark.asyncio
async def test_file_dispute(client, auth_headers):
    # Create project
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Dispute Test"},
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/projects/{project_id}/disputes",
        headers=auth_headers,
        json={
            "title": "Foundation crack",
            "description": "Noticed a crack in the foundation wall after pour",
            "dispute_type": "quality",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "identified"
    assert data["dispute_type"] == "quality"
    assert data["title"] == "Foundation crack"


@pytest.mark.asyncio
async def test_list_disputes(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "List Disputes Test"},
    )
    project_id = create_resp.json()["id"]

    # File a dispute
    await client.post(
        f"/api/v1/projects/{project_id}/disputes",
        headers=auth_headers,
        json={
            "title": "Timeline issue",
            "description": "Work is 2 weeks behind",
            "dispute_type": "timeline",
        },
    )

    response = await client.get(
        f"/api/v1/projects/{project_id}/disputes",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_update_dispute_respond(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Respond Test"},
    )
    project_id = create_resp.json()["id"]

    dispute_resp = await client.post(
        f"/api/v1/projects/{project_id}/disputes",
        headers=auth_headers,
        json={
            "title": "Budget dispute",
            "description": "Costs exceeding estimate",
            "dispute_type": "budget",
        },
    )
    dispute_id = dispute_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/projects/{project_id}/disputes/{dispute_id}",
        headers=auth_headers,
        json={"action": "respond", "response_text": "We need to review the scope"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "direct_resolution"


@pytest.mark.asyncio
async def test_update_dispute_escalate(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Escalate Test"},
    )
    project_id = create_resp.json()["id"]

    dispute_resp = await client.post(
        f"/api/v1/projects/{project_id}/disputes",
        headers=auth_headers,
        json={
            "title": "Quality issue",
            "description": "Poor workmanship",
            "dispute_type": "quality",
        },
    )
    dispute_id = dispute_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/projects/{project_id}/disputes/{dispute_id}",
        headers=auth_headers,
        json={"action": "escalate"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "direct_resolution"


@pytest.mark.asyncio
async def test_update_dispute_resolve(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Resolve Test"},
    )
    project_id = create_resp.json()["id"]

    dispute_resp = await client.post(
        f"/api/v1/projects/{project_id}/disputes",
        headers=auth_headers,
        json={
            "title": "Scope dispute",
            "description": "Extra work not in contract",
            "dispute_type": "scope",
        },
    )
    dispute_id = dispute_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/projects/{project_id}/disputes/{dispute_id}",
        headers=auth_headers,
        json={"action": "resolve", "resolution": "Agreed to split cost 50/50"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert response.json()["resolution"] == "Agreed to split cost 50/50"
