"""Integration tests for the alerts API (CRUD, validation, ownership)."""
from datetime import datetime, timezone

import pytest

from main import app
from market_data.models import MarketData
from stocks.models import Stock

pytestmark = pytest.mark.asyncio


async def _auth(client, email="alerter@x.com") -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass1234", "role": "trader"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _seed_stock(symbol: str, price: float = 500.0) -> None:
    async with app.state.test_session() as s:
        stock = Stock(symbol=symbol, company_name=f"{symbol} Ltd", sector="Bank")
        s.add(stock)
        await s.flush()
        s.add(MarketData(stock_id=stock.id, open_price=price, high_price=price,
                         low_price=price, close_price=price, volume=1000,
                         timestamp=datetime.now(timezone.utc)))
        await s.commit()


def _price_alert(symbol="NABIL", **over):
    body = {"symbol": symbol, "alert_type": "price", "condition": "above",
            "threshold_value": 600}
    body.update(over)
    return body


async def test_create_requires_auth(client):
    r = await client.post("/api/v1/alerts", json=_price_alert())
    assert r.status_code in (401, 403)


async def test_create_and_list_alert(client):
    headers = await _auth(client)
    await _seed_stock("NABIL")

    r = await client.post("/api/v1/alerts", json=_price_alert(), headers=headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["stock_symbol"] == "NABIL"
    assert body["is_active"] is True
    assert body["trigger_count"] == 0

    listed = (await client.get("/api/v1/alerts", headers=headers)).json()
    assert len(listed) == 1 and listed[0]["id"] == body["id"]


async def test_create_unknown_symbol_404(client):
    headers = await _auth(client)
    r = await client.post("/api/v1/alerts", json=_price_alert("GHOST"), headers=headers)
    assert r.status_code == 404


async def test_threshold_must_be_positive(client):
    headers = await _auth(client)
    await _seed_stock("NABIL")
    r = await client.post("/api/v1/alerts",
                          json=_price_alert(threshold_value=-1), headers=headers)
    assert r.status_code == 422


async def test_equal_requires_tolerance(client):
    headers = await _auth(client)
    await _seed_stock("NABIL")
    r = await client.post("/api/v1/alerts",
                          json=_price_alert(condition="equal"), headers=headers)
    assert r.status_code == 422


async def test_volume_only_allows_above(client):
    headers = await _auth(client)
    await _seed_stock("NABIL")
    r = await client.post(
        "/api/v1/alerts",
        json=_price_alert(alert_type="volume", condition="below", threshold_value=2),
        headers=headers,
    )
    assert r.status_code == 422


async def test_update_and_deactivate(client):
    headers = await _auth(client)
    await _seed_stock("NABIL")
    alert_id = (await client.post("/api/v1/alerts", json=_price_alert(),
                                  headers=headers)).json()["id"]

    r = await client.patch(f"/api/v1/alerts/{alert_id}",
                           json={"threshold_value": 700, "is_active": False},
                           headers=headers)
    assert r.status_code == 200
    assert r.json()["threshold_value"] == 700
    assert r.json()["is_active"] is False


async def test_delete_alert(client):
    headers = await _auth(client)
    await _seed_stock("NABIL")
    alert_id = (await client.post("/api/v1/alerts", json=_price_alert(),
                                  headers=headers)).json()["id"]
    r = await client.delete(f"/api/v1/alerts/{alert_id}", headers=headers)
    assert r.status_code == 204
    assert (await client.get("/api/v1/alerts", headers=headers)).json() == []


async def test_ownership_isolation(client):
    owner = await _auth(client, "owner@x.com")
    await _seed_stock("NABIL")
    alert_id = (await client.post("/api/v1/alerts", json=_price_alert(),
                                  headers=owner)).json()["id"]

    intruder = await _auth(client, "intruder@x.com")
    r = await client.get(f"/api/v1/alerts/{alert_id}", headers=intruder)
    assert r.status_code == 404
    assert (await client.get("/api/v1/alerts", headers=intruder)).json() == []
