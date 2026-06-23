"""Integration tests for the analytics dashboard API.

Live aggregations read the Redis snapshot, which is absent in tests, so they
return the well-formed empty state. The technical endpoint is exercised against
seeded OHLCV history.
"""
from datetime import datetime, timedelta, timezone

import pytest

from main import app
from market_data.models import MarketData
from stocks.models import Stock

pytestmark = pytest.mark.asyncio


async def _auth(client, email="analyst@x.com") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "role": "trader"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _seed_history(symbol: str, n: int) -> None:
    base = datetime.now(timezone.utc) - timedelta(minutes=n)
    async with app.state.test_session() as s:
        stock = Stock(symbol=symbol, company_name=f"{symbol} Ltd", sector="Bank")
        s.add(stock)
        await s.flush()
        for i in range(n):
            price = 100.0 + i  # steadily rising series
            s.add(MarketData(
                stock_id=stock.id, open_price=price, high_price=price + 1,
                low_price=price - 1, close_price=price, volume=1000 + i,
                timestamp=base + timedelta(minutes=i),
            ))
        await s.commit()


async def test_requires_auth(client):
    assert (await client.get("/api/v1/analytics/overview")).status_code in (401, 403)


async def test_overview_empty_state(client):
    headers = await _auth(client)
    r = await client.get("/api/v1/analytics/overview", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total_stocks"] == 0
    assert body["sentiment"] == "Neutral"


async def test_sectors_gainers_losers_heatmap_return_lists(client):
    headers = await _auth(client)
    for path in ("/analytics/sectors", "/analytics/gainers",
                 "/analytics/losers", "/analytics/heatmap"):
        r = await client.get(f"/api/v1{path}", headers=headers)
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)


async def test_heatmap_rejects_bad_mode(client):
    headers = await _auth(client)
    r = await client.get("/api/v1/analytics/heatmap?mode=bogus", headers=headers)
    assert r.status_code == 422


async def test_market_ai_insights(client):
    headers = await _auth(client)
    r = await client.get("/api/v1/analytics/ai-insights", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["scope"] == "market"
    assert isinstance(r.json()["insights"], list)


async def test_technical_indicators_full(client):
    headers = await _auth(client)
    await _seed_history("NABIL", 60)
    r = await client.get("/api/v1/analytics/technical/NABIL?timeframe=1M",
                         headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["symbol"] == "NABIL" and body["points"] == 60
    assert "rsi" in body["series"] and "macd" in body["series"]
    assert body["latest"]["price"] == 159.0  # 100 + 59
    assert body["suggestion"]["action"] in {"BUY", "SELL", "HOLD"}
    assert isinstance(body["insights"], list)


async def test_technical_insufficient_history(client):
    headers = await _auth(client)
    await _seed_history("NICA", 10)  # below ANALYTICS_MIN_HISTORY
    r = await client.get("/api/v1/analytics/technical/NICA", headers=headers)
    assert r.status_code == 422


async def test_technical_unknown_symbol(client):
    headers = await _auth(client)
    r = await client.get("/api/v1/analytics/technical/GHOST", headers=headers)
    assert r.status_code == 404


async def test_symbol_ai_insights(client):
    headers = await _auth(client)
    await _seed_history("GBIME", 60)
    r = await client.get("/api/v1/analytics/ai-insights/GBIME", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["scope"] == "GBIME"
    assert r.json()["suggestion"]["action"] in {"BUY", "SELL", "HOLD"}
