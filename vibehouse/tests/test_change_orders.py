import pytest


@pytest.mark.asyncio
async def test_create_change_order(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "CO Test", "budget": 300000},
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/projects/{project_id}/change-orders",
        headers=auth_headers,
        json={
            "title": "Add extra bathroom",
            "description": "Homeowner wants an additional bathroom on 2nd floor",
            "reason": "client_request",
            "cost_impact": 15000,
            "schedule_impact_days": 7,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Add extra bathroom"
    assert data["status"] == "pending"
    assert data["cost_impact"] == "15000.00"
    assert data["schedule_impact_days"] == 7


@pytest.mark.asyncio
async def test_create_change_order_invalid_reason(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "CO Invalid Test"},
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/projects/{project_id}/change-orders",
        headers=auth_headers,
        json={
            "title": "Bad reason",
            "description": "Some change",
            "reason": "invalid_reason",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_change_orders(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "CO List Test"},
    )
    project_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/change-orders",
        headers=auth_headers,
        json={
            "title": "Add solar panels",
            "description": "Upgrade to solar",
            "reason": "scope_change",
            "cost_impact": 25000,
        },
    )

    response = await client.get(
        f"/api/v1/projects/{project_id}/change-orders",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_approve_change_order(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "CO Approve Test"},
    )
    project_id = create_resp.json()["id"]

    co_resp = await client.post(
        f"/api/v1/projects/{project_id}/change-orders",
        headers=auth_headers,
        json={
            "title": "Upgrade countertops",
            "description": "Switch to granite",
            "reason": "client_request",
            "cost_impact": 5000,
        },
    )
    co_id = co_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/projects/{project_id}/change-orders/{co_id}",
        headers=auth_headers,
        json={"action": "approve", "notes": "Looks good"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_reject_change_order(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "CO Reject Test"},
    )
    project_id = create_resp.json()["id"]

    co_resp = await client.post(
        f"/api/v1/projects/{project_id}/change-orders",
        headers=auth_headers,
        json={
            "title": "Gold fixtures",
            "description": "Too expensive",
            "reason": "client_request",
            "cost_impact": 50000,
        },
    )
    co_id = co_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/projects/{project_id}/change-orders/{co_id}",
        headers=auth_headers,
        json={"action": "reject"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_implement_change_order(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "CO Implement Test", "budget": 100000},
    )
    project_id = create_resp.json()["id"]

    co_resp = await client.post(
        f"/api/v1/projects/{project_id}/change-orders",
        headers=auth_headers,
        json={
            "title": "Add deck",
            "description": "Backyard deck",
            "reason": "scope_change",
            "cost_impact": 10000,
        },
    )
    co_id = co_resp.json()["id"]

    # Approve first
    await client.patch(
        f"/api/v1/projects/{project_id}/change-orders/{co_id}",
        headers=auth_headers,
        json={"action": "approve"},
    )

    # Then implement
    response = await client.patch(
        f"/api/v1/projects/{project_id}/change-orders/{co_id}",
        headers=auth_headers,
        json={"action": "implement"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "implemented"


@pytest.mark.asyncio
async def test_invalid_transition(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "CO Bad Transition"},
    )
    project_id = create_resp.json()["id"]

    co_resp = await client.post(
        f"/api/v1/projects/{project_id}/change-orders",
        headers=auth_headers,
        json={
            "title": "Skip to implement",
            "description": "Should fail",
            "reason": "error",
        },
    )
    co_id = co_resp.json()["id"]

    # Try to implement without approving
    response = await client.patch(
        f"/api/v1/projects/{project_id}/change-orders/{co_id}",
        headers=auth_headers,
        json={"action": "implement"},
    )
    assert response.status_code == 400
