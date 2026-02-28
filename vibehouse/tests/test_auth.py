import pytest


@pytest.mark.asyncio
async def test_register(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@test.com",
            "password": "securepass123",
            "full_name": "New User",
            "role": "homeowner",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["full_name"] == "New User"
    assert data["role"] == "homeowner"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {
        "email": "duplicate@test.com",
        "password": "securepass123",
        "full_name": "First User",
    }
    await client.post("/api/v1/auth/register", json=payload)

    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login(client):
    # Register first
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@test.com",
            "password": "mypassword",
            "full_name": "Login User",
        },
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@test.com", "password": "mypassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "wrong"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_me(client, auth_headers):
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "homeowner"
    assert "email" in data


@pytest.mark.asyncio
async def test_get_me_no_auth(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refresh_token(client):
    # Register and login
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@test.com",
            "password": "mypassword",
            "full_name": "Refresh User",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@test.com", "password": "mypassword"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # Refresh
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
