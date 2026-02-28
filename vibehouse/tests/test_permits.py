import pytest


@pytest.mark.asyncio
async def test_create_permit(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Permit Test"},
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/projects/{project_id}/permits",
        headers=auth_headers,
        json={
            "permit_type": "building",
            "jurisdiction": "Austin, TX",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["permit_type"] == "building"
    assert data["status"] == "not_applied"


@pytest.mark.asyncio
async def test_list_permits(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Permit List Test"},
    )
    project_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/permits",
        headers=auth_headers,
        json={"permit_type": "electrical", "jurisdiction": "TX"},
    )

    response = await client.get(
        f"/api/v1/projects/{project_id}/permits",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_update_permit_status(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Permit Update Test"},
    )
    project_id = create_resp.json()["id"]

    permit_resp = await client.post(
        f"/api/v1/projects/{project_id}/permits",
        headers=auth_headers,
        json={"permit_type": "plumbing", "jurisdiction": "TX"},
    )
    permit_id = permit_resp.json()["id"]

    # Transition: not_applied -> applied
    response = await client.patch(
        f"/api/v1/projects/{project_id}/permits/{permit_id}",
        headers=auth_headers,
        json={"status": "applied", "application_number": "PLM-2026-001"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "applied"
    assert response.json()["application_number"] == "PLM-2026-001"


@pytest.mark.asyncio
async def test_permit_invalid_transition(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Permit Bad Transition"},
    )
    project_id = create_resp.json()["id"]

    permit_resp = await client.post(
        f"/api/v1/projects/{project_id}/permits",
        headers=auth_headers,
        json={"permit_type": "building", "jurisdiction": "TX"},
    )
    permit_id = permit_resp.json()["id"]

    # not_applied -> approved is invalid
    response = await client.patch(
        f"/api/v1/projects/{project_id}/permits/{permit_id}",
        headers=auth_headers,
        json={"status": "approved"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_permit_checklist(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Checklist Test", "address": "123 Main St, Austin, TX 78701"},
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/projects/{project_id}/permits/checklist",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["jurisdiction"] == "TX"
    assert len(data["items"]) >= 6  # At least the core permits
    assert data["completion_percent"] == 0.0

    # Texas should have Foundation Soil Report
    item_names = [item["name"] for item in data["items"]]
    assert "Foundation Soil Report" in item_names
