"""Integration tests for the Phase 10 mobile API."""
import pytest

pytestmark = pytest.mark.asyncio

BIG_TS = 9_999_999_999_999  # far-future epoch ms → always wins LWW


async def _auth(client, email="mobile@x.com") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "role": "trader"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---- Watchlist ----
async def test_watchlist_add_list_remove(client):
    h = await _auth(client)
    r = await client.post("/api/v1/mobile/watchlist", json={"symbol": "nabil"}, headers=h)
    assert r.status_code == 201 and r.json() == ["NABIL"]

    await client.post("/api/v1/mobile/watchlist", json={"symbol": "UPPER"}, headers=h)
    assert (await client.get("/api/v1/mobile/watchlist", headers=h)).json() == ["NABIL", "UPPER"]

    assert (await client.delete("/api/v1/mobile/watchlist/NABIL", headers=h)).status_code == 204
    assert (await client.get("/api/v1/mobile/watchlist", headers=h)).json() == ["UPPER"]


async def test_sync_client_wins_when_newer(client):
    h = await _auth(client)
    await client.post("/api/v1/mobile/watchlist", json={"symbol": "UPPER"}, headers=h)
    await client.post("/api/v1/mobile/watchlist", json={"symbol": "CHCL"}, headers=h)

    # Client adds NABIL and deletes UPPER, both with far-future timestamps.
    body = {"items": [
        {"symbol": "NABIL", "updated_at": BIG_TS, "deleted": False},
        {"symbol": "UPPER", "updated_at": BIG_TS, "deleted": True},
    ]}
    r = await client.post("/api/v1/mobile/watchlist/sync", json=body, headers=h)
    assert r.status_code == 200
    # CHCL untouched (server-only), NABIL added, UPPER tombstoned.
    assert r.json()["symbols"] == ["CHCL", "NABIL"]
    tomb = {i["symbol"]: i["deleted"] for i in r.json()["items"]}
    assert tomb["UPPER"] is True and tomb["NABIL"] is False


async def test_sync_server_wins_when_client_stale(client):
    h = await _auth(client)
    await client.post("/api/v1/mobile/watchlist", json={"symbol": "UPPER"}, headers=h)

    # Client tries to delete UPPER with a stale timestamp → server add wins.
    body = {"items": [{"symbol": "UPPER", "updated_at": 1, "deleted": True}]}
    r = await client.post("/api/v1/mobile/watchlist/sync", json=body, headers=h)
    assert "UPPER" in r.json()["symbols"]


# ---- Device tokens ----
async def test_device_register_dedupe_delete(client):
    h = await _auth(client)
    reg = await client.post(
        "/api/v1/mobile/devices",
        json={"token": "fcm-token-abcdef123456", "platform": "android"},
        headers=h,
    )
    assert reg.status_code == 201
    assert "*" in reg.json()["token"]  # masked

    # Re-registering the same token is idempotent.
    await client.post(
        "/api/v1/mobile/devices",
        json={"token": "fcm-token-abcdef123456", "platform": "android"},
        headers=h,
    )
    assert len((await client.get("/api/v1/mobile/devices", headers=h)).json()) == 1

    d = await client.delete(
        "/api/v1/mobile/devices", params={"token": "fcm-token-abcdef123456"}, headers=h
    )
    assert d.status_code == 204
    assert (await client.get("/api/v1/mobile/devices", headers=h)).json() == []


# ---- Preferences ----
async def test_preferences_defaults_and_update(client):
    h = await _auth(client)
    p = (await client.get("/api/v1/mobile/preferences", headers=h)).json()
    assert p["push_enabled"] is True and p["sms_enabled"] is False

    upd = {**p, "push_enabled": False, "sms_enabled": True}
    r = await client.put("/api/v1/mobile/preferences", json=upd, headers=h)
    assert r.status_code == 200
    assert r.json()["push_enabled"] is False and r.json()["sms_enabled"] is True


# ---- Aggregated home ----
async def test_mobile_home_shape(client):
    h = await _auth(client)
    r = await client.get("/api/v1/mobile/home", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"overview", "watchlist", "portfolio", "preferences"}
    assert body["overview"]["total_stocks"] == 0       # no live snapshot in tests
    assert body["portfolio"]["cash_balance"] == 1_000_000.0
    assert body["preferences"]["push_enabled"] is True
