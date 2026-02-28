import pytest


@pytest.mark.asyncio
async def test_search_vendors(client, auth_headers):
    # Create project
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Vendor Search Test"},
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/projects/{project_id}/vendors/search",
        headers=auth_headers,
        json={"trade": "plumbing", "radius_miles": 30},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert "message" in data


@pytest.mark.asyncio
async def test_list_bids_empty(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Bids Test"},
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/projects/{project_id}/vendors/bids",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0
