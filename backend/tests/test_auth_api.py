"""API tests for the auth flow (register -> login -> refresh -> protected)."""
import pytest

pytestmark = pytest.mark.asyncio


async def test_register_login_refresh_and_me(client):
    # Register
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": "trader@example.com", "password": "pass1234", "role": "trader"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "trader@example.com"

    # Duplicate registration is rejected
    r_dup = await client.post(
        "/api/v1/auth/register",
        json={"email": "trader@example.com", "password": "pass1234"},
    )
    assert r_dup.status_code == 409

    # Login
    r_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "trader@example.com", "password": "pass1234"},
    )
    assert r_login.status_code == 200, r_login.text
    tokens = r_login.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    # Protected /users/me with the access token
    r_me = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r_me.status_code == 200
    assert r_me.json()["role"] == "trader"

    # Refresh issues a new pair
    r_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert r_refresh.status_code == 200
    assert r_refresh.json()["access_token"]


async def test_login_with_wrong_password(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "x@example.com", "password": "correct-pass"},
    )
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": "x@example.com", "password": "wrong-pass"},
    )
    assert r.status_code == 401


async def test_protected_route_requires_token(client):
    r = await client.get("/api/v1/users/me")
    assert r.status_code in (401, 403)
