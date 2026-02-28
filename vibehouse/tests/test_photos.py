import pytest


@pytest.mark.asyncio
async def test_upload_photo(client, auth_headers):
    # Create project
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Photo Test"},
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/projects/{project_id}/photos",
        headers=auth_headers,
        json={
            "file_url": "https://storage.example.com/photos/foundation.jpg",
            "caption": "Foundation pour complete",
            "tags": ["foundation", "concrete"],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["file_url"] == "https://storage.example.com/photos/foundation.jpg"
    assert data["caption"] == "Foundation pour complete"
    assert data["tags"] == ["foundation", "concrete"]


@pytest.mark.asyncio
async def test_list_photos_paginated(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Photo List Test"},
    )
    project_id = create_resp.json()["id"]

    # Upload a few photos
    for i in range(3):
        await client.post(
            f"/api/v1/projects/{project_id}/photos",
            headers=auth_headers,
            json={"file_url": f"https://storage.example.com/photo_{i}.jpg"},
        )

    response = await client.get(
        f"/api/v1/projects/{project_id}/photos",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_photo_progress_summary(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Progress Test"},
    )
    project_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/photos",
        headers=auth_headers,
        json={"file_url": "https://storage.example.com/progress.jpg"},
    )

    response = await client.get(
        f"/api/v1/projects/{project_id}/photos/progress",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_photos"] == 1
    assert data["photos_this_week"] == 1
    assert data["latest_photo"] is not None
