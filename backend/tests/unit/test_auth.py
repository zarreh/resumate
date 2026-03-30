"""Tests for auth endpoints: register, login, refresh, me."""

import uuid

from httpx import AsyncClient


async def test_register_success(client: AsyncClient) -> None:
    email = f"register-{uuid.uuid4().hex[:8]}@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={"name": "New User", "email": email, "password": "strongpass123"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_register_duplicate_email(client: AsyncClient, registered_user: dict) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"name": "Dup", "email": registered_user["email"], "password": "pass123"},
    )
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"]


async def test_login_success(client: AsyncClient, registered_user: dict) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


async def test_login_wrong_password(client: AsyncClient, registered_user: dict) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": "wrongpassword"},
    )
    assert resp.status_code == 401


async def test_login_nonexistent_user(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "noone@example.com", "password": "pass123"},
    )
    assert resp.status_code == 401


async def test_refresh_token(client: AsyncClient, registered_user: dict) -> None:
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered_user["refresh_token"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # New refresh token should differ (rotation)
    assert data["refresh_token"] != registered_user["refresh_token"]


async def test_refresh_token_invalid(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )
    assert resp.status_code == 401


async def test_refresh_token_reuse_blocked(client: AsyncClient, registered_user: dict) -> None:
    """Using the same refresh token twice should fail (token rotation)."""
    # First use — should succeed
    resp1 = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered_user["refresh_token"]},
    )
    assert resp1.status_code == 200

    # Second use of same token — should fail (already rotated)
    resp2 = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": registered_user["refresh_token"]},
    )
    assert resp2.status_code == 401


async def test_me_authenticated(
    client: AsyncClient, registered_user: dict, auth_headers: dict[str, str]
) -> None:
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == registered_user["email"]
    assert data["name"] == registered_user["name"]


async def test_me_no_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 403  # HTTPBearer returns 403 when no credentials


async def test_me_invalid_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid-token"})
    assert resp.status_code == 401


async def test_health_check(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
