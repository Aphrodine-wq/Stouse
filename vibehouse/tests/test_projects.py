import pytest


@pytest.mark.asyncio
async def test_create_project(client, auth_headers):
    response = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={
            "title": "My Dream Home",
            "vibe_description": "Modern 3 bedroom house with open floor plan",
            "address": "123 Main St, Austin, TX",
            "budget": 350000,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My Dream Home"
    assert data["status"] == "draft"
    assert data["budget"] == "350000.00"


@pytest.mark.asyncio
async def test_list_projects(client, auth_headers):
    # Create a project first
    await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Test House", "budget": 200000},
    )

    response = await client.get("/api/v1/projects", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["projects"]) >= 1


@pytest.mark.asyncio
async def test_get_project(client, auth_headers):
    # Create
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Get Test House"},
    )
    project_id = create_resp.json()["id"]

    # Get
    response = await client.get(f"/api/v1/projects/{project_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Get Test House"


@pytest.mark.asyncio
async def test_update_project(client, auth_headers):
    # Create
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Update Test"},
    )
    project_id = create_resp.json()["id"]

    # Update title
    response = await client.patch(
        f"/api/v1/projects/{project_id}",
        headers=auth_headers,
        json={"title": "Updated Title", "budget": 500000},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Title"
    assert response.json()["budget"] == "500000.00"


@pytest.mark.asyncio
async def test_project_status_transition(client, auth_headers):
    # Create
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Transition Test"},
    )
    project_id = create_resp.json()["id"]

    # Valid transition: draft -> designing
    response = await client.patch(
        f"/api/v1/projects/{project_id}",
        headers=auth_headers,
        json={"status": "designing"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "designing"


@pytest.mark.asyncio
async def test_invalid_status_transition(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Bad Transition"},
    )
    project_id = create_resp.json()["id"]

    # Invalid transition: draft -> completed
    response = await client.patch(
        f"/api/v1/projects/{project_id}",
        headers=auth_headers,
        json={"status": "completed"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_project_not_found(client, auth_headers):
    response = await client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert response.status_code == 404
