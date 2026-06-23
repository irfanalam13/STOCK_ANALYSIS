"""Unit tests for Phase 8 security primitives (no DB / no Redis)."""
import pytest
from fastapi import HTTPException

from security import apikey, encryption
from security.ratelimit import check_rate_limit
from security.ws_guard import MessageRateLimiter
from security.rbac import (
    P_ADMIN_AUDIT,
    P_PORTFOLIO_TRADE,
    has_permission,
    rate_limit_for_role,
)
from users.models import UserRole


# ---- Encryption ----
def test_encrypt_decrypt_roundtrip():
    secret = "sk_live_abc123"
    token = encryption.encrypt(secret)
    assert token != secret
    assert encryption.decrypt(token) == secret


def test_decrypt_tampered_raises():
    token = encryption.encrypt("data")
    with pytest.raises(ValueError):
        encryption.decrypt(token[:-2] + "xy")


def test_mask_keeps_tail():
    assert encryption.mask("sk_live_abcd") == "********abcd"
    assert encryption.mask("ab") == "**"


# ---- RBAC matrix ----
def test_admin_has_every_permission():
    assert has_permission(UserRole.ADMIN, P_ADMIN_AUDIT)
    assert has_permission(UserRole.ADMIN, P_PORTFOLIO_TRADE)


def test_viewer_cannot_trade_or_audit():
    assert not has_permission(UserRole.VIEWER, P_PORTFOLIO_TRADE)
    assert not has_permission(UserRole.VIEWER, P_ADMIN_AUDIT)


def test_trader_can_trade_not_audit():
    assert has_permission(UserRole.TRADER, P_PORTFOLIO_TRADE)
    assert not has_permission(UserRole.TRADER, P_ADMIN_AUDIT)


def test_rate_limit_tiers():
    assert rate_limit_for_role("admin") > rate_limit_for_role("trader")
    assert rate_limit_for_role("trader") > rate_limit_for_role("viewer")
    assert rate_limit_for_role(None) > 0  # anonymous still gets a budget


# ---- Rate-limit counter ----
class FakeAsyncRedis:
    def __init__(self):
        self.counts: dict[str, int] = {}

    async def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key, window):
        return True

    async def ttl(self, key):
        return 30


@pytest.mark.asyncio
async def test_check_rate_limit_allows_then_blocks():
    redis = FakeAsyncRedis()
    allowed1, c1, _ = await check_rate_limit(redis, "k", 2, 60)
    allowed2, c2, _ = await check_rate_limit(redis, "k", 2, 60)
    allowed3, c3, _ = await check_rate_limit(redis, "k", 2, 60)
    assert (allowed1, allowed2, allowed3) == (True, True, False)
    assert (c1, c2, c3) == (1, 2, 3)


# ---- WebSocket message limiter (sliding window, injected time) ----
def test_ws_limiter_blocks_burst_then_recovers():
    lim = MessageRateLimiter(limit=3, window=10)
    assert [lim.allow(now=t) for t in (0, 1, 2)] == [True, True, True]
    assert lim.allow(now=3) is False          # 4th within window → blocked
    assert lim.allow(now=12) is True          # window slid past first events


# ---- API key ----
@pytest.mark.asyncio
async def test_require_api_key(monkeypatch):
    monkeypatch.setattr(apikey.settings, "API_KEYS", "key1,key2")
    assert await apikey.require_api_key("key1") == "key1"
    with pytest.raises(HTTPException):
        await apikey.require_api_key("bad")
    with pytest.raises(HTTPException):
        await apikey.require_api_key(None)
