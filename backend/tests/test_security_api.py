"""Integration tests for Phase 8 security: headers, RBAC, audit, fraud, limits."""
from datetime import datetime, timezone

import pytest

import security.ratelimit as ratelimit
from main import app
from security.models import AuditLog

pytestmark = pytest.mark.asyncio


async def _auth(client, email, role="viewer") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "role": role},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ---- Security headers ----
async def test_security_headers_present(client):
    r = await client.get("/health")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"
    assert "referrer-policy" in r.headers


# ---- RBAC / permissions ----
async def test_permissions_endpoint_tiers(client):
    viewer = await _auth(client, "v@x.com", "viewer")
    trader = await _auth(client, "t@x.com", "trader")
    admin = await _auth(client, "a@x.com", "admin")

    v = (await client.get("/api/v1/security/me/permissions", headers=viewer)).json()
    t = (await client.get("/api/v1/security/me/permissions", headers=trader)).json()
    a = (await client.get("/api/v1/security/me/permissions", headers=admin)).json()

    assert v["rate_limit_per_minute"] == 100
    assert t["rate_limit_per_minute"] == 1000
    assert a["rate_limit_per_minute"] == 5000
    assert "*" in a["permissions"]
    assert "portfolio:trade" in t["permissions"]
    assert "portfolio:trade" not in v["permissions"]


async def test_audit_endpoint_requires_admin(client):
    viewer = await _auth(client, "v2@x.com", "viewer")
    admin = await _auth(client, "a2@x.com", "admin")
    assert (await client.get("/api/v1/security/audit", headers=viewer)).status_code == 403
    assert (await client.get("/api/v1/security/audit", headers=admin)).status_code == 200


# ---- Audit middleware end-to-end ----
async def test_mutation_is_audited(client):
    admin = await _auth(client, "a3@x.com", "admin")
    # A mutating request that should be auto-audited by the middleware.
    r = await client.patch("/api/v1/users/me", json={"phone": "+97798"}, headers=admin)
    assert r.status_code == 200

    logs = (await client.get("/api/v1/security/audit", headers=admin)).json()
    assert any(entry["path"] == "/api/v1/users/me" and entry["method"] == "PATCH"
               for entry in logs)


# ---- Fraud detection ----
async def _seed_trades(user_id: int, n: int) -> None:
    async with app.state.test_session() as s:
        for _ in range(n):
            s.add(AuditLog(
                user_id=user_id, action="POST /api/v1/portfolio/buy",
                method="POST", path="/api/v1/portfolio/buy", status_code=201,
                timestamp=datetime.now(timezone.utc),
            ))
        await s.commit()


async def test_fraud_scan_flags_rapid_trading(client):
    admin = await _auth(client, "a4@x.com", "admin")
    trader = await _auth(client, "trader4@x.com", "trader")
    me = (await client.get("/api/v1/users/me", headers=trader)).json()

    await _seed_trades(me["id"], 25)  # over FRAUD_MAX_TRADES (20)

    scan = await client.post("/api/v1/security/fraud/scan", headers=admin)
    assert scan.status_code == 200
    assert scan.json()["flags_raised"] >= 1

    flags = (await client.get("/api/v1/security/fraud/flags", headers=admin)).json()
    rapid = [f for f in flags if f["reason"] == "rapid_trading"]
    assert rapid and rapid[0]["user_id"] == me["id"]

    # Resolve it.
    fid = rapid[0]["id"]
    res = await client.patch(f"/api/v1/security/fraud/flags/{fid}/resolve", headers=admin)
    assert res.status_code == 200 and res.json()["resolved"] is True


# ---- Rate limiting ----
class _FakeRedis:
    def __init__(self):
        self.counts: dict[str, int] = {}

    async def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key, window):
        return True

    async def ttl(self, key):
        return 30


async def test_rate_limit_returns_429(client, monkeypatch):
    fake = _FakeRedis()
    monkeypatch.setattr(ratelimit, "get_redis", lambda: fake)
    monkeypatch.setattr(ratelimit.settings, "RATE_LIMIT_ANON", 2)
    app.state.rate_limit_enabled = True
    try:
        statuses = [
            (await client.get("/api/v1/stocks")).status_code for _ in range(3)
        ]
    finally:
        app.state.rate_limit_enabled = False
    # First two pass the limiter (then 401 unauth); the third is throttled.
    assert statuses[-1] == 429
    assert statuses[0] != 429
