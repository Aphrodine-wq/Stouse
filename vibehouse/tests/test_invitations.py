import pytest


@pytest.mark.asyncio
async def test_create_invitation(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Invitation Test"},
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/projects/{project_id}/invitations",
        headers=auth_headers,
        json={
            "email": "contractor@example.com",
            "role": "contractor",
            "message": "Please join our project!",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "contractor@example.com"
    assert data["role"] == "contractor"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_create_invitation_invalid_role(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Bad Role Test"},
    )
    project_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/projects/{project_id}/invitations",
        headers=auth_headers,
        json={"email": "someone@example.com", "role": "homeowner"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_invitations(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "List Invitations Test"},
    )
    project_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/invitations",
        headers=auth_headers,
        json={"email": "inspector@example.com", "role": "inspector"},
    )

    response = await client.get(
        f"/api/v1/projects/{project_id}/invitations",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_revoke_invitation(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Revoke Test"},
    )
    project_id = create_resp.json()["id"]

    invite_resp = await client.post(
        f"/api/v1/projects/{project_id}/invitations",
        headers=auth_headers,
        json={"email": "revoke@example.com", "role": "contractor"},
    )
    invite_id = invite_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/projects/{project_id}/invitations/{invite_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Invitation revoked"


@pytest.mark.asyncio
async def test_duplicate_invitation(client, auth_headers):
    create_resp = await client.post(
        "/api/v1/projects",
        headers=auth_headers,
        json={"title": "Duplicate Test"},
    )
    project_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/projects/{project_id}/invitations",
        headers=auth_headers,
        json={"email": "dup@example.com", "role": "contractor"},
    )

    # Second attempt should fail
    response = await client.post(
        f"/api/v1/projects/{project_id}/invitations",
        headers=auth_headers,
        json={"email": "dup@example.com", "role": "contractor"},
    )
    assert response.status_code == 400
