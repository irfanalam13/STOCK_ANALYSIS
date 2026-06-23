"""Tests for the self-service profile endpoint (Phase 6: SMS phone number)."""
import pytest

pytestmark = pytest.mark.asyncio


async def _auth(client, email="profile@x.com") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "role": "trader"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_me_phone_defaults_to_null(client):
    headers = await _auth(client)
    me = (await client.get("/api/v1/users/me", headers=headers)).json()
    assert me["phone"] is None


async def test_update_and_clear_phone(client):
    headers = await _auth(client)

    r = await client.patch("/api/v1/users/me", json={"phone": "+9779800000000"},
                           headers=headers)
    assert r.status_code == 200
    assert r.json()["phone"] == "+9779800000000"

    # Clearing the number sets it back to null.
    r = await client.patch("/api/v1/users/me", json={"phone": None}, headers=headers)
    assert r.status_code == 200
    assert r.json()["phone"] is None


async def test_update_requires_auth(client):
    r = await client.patch("/api/v1/users/me", json={"phone": "123"})
    assert r.status_code in (401, 403)
