"""End-to-end paper-trading tests: buy, sell, P/L, summary, analytics."""
from datetime import datetime, timezone

import pytest

from main import app
from market_data.models import MarketData
from stocks.models import Stock

pytestmark = pytest.mark.asyncio

INITIAL = 1_000_000.0


async def _auth(client) -> dict:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "trader@x.com", "password": "pass1234", "role": "trader"},
    )
    r = await client.post(
        "/api/v1/auth/login", json={"email": "trader@x.com", "password": "pass1234"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _seed_stock(symbol: str, price: float) -> None:
    async with app.state.test_session() as s:
        stock = Stock(symbol=symbol, company_name=f"{symbol} Ltd", sector="Commercial Bank")
        s.add(stock)
        await s.flush()
        s.add(
            MarketData(
                stock_id=stock.id, open_price=price, high_price=price,
                low_price=price, close_price=price, volume=1000,
                timestamp=datetime.now(timezone.utc),
            )
        )
        await s.commit()


async def test_buy_updates_cash_and_holding(client):
    headers = await _auth(client)
    await _seed_stock("NABIL", 500.0)

    r = await client.post("/api/v1/portfolio/buy",
                          json={"symbol": "NABIL", "quantity": 10}, headers=headers)
    assert r.status_code == 201, r.text
    assert r.json()["price"] == 500.0

    summary = (await client.get("/api/v1/portfolio/summary", headers=headers)).json()
    # 10 * 500 = 5000 gross + 0.4% fee (20) = 5020 spent.
    assert summary["cash_balance"] == round(INITIAL - 5020.0, 2)
    assert len(summary["holdings"]) == 1
    h = summary["holdings"][0]
    assert h["symbol"] == "NABIL" and h["quantity"] == 10
    assert h["avg_buy_price"] == 500.0


async def test_insufficient_funds_rejected(client):
    headers = await _auth(client)
    await _seed_stock("HDL", 1180.0)
    r = await client.post("/api/v1/portfolio/buy",
                          json={"symbol": "HDL", "quantity": 100000}, headers=headers)
    assert r.status_code == 400
    assert "Insufficient funds" in r.json()["detail"]


async def test_sell_realizes_pnl_and_analytics(client):
    headers = await _auth(client)
    await _seed_stock("NICA", 400.0)

    await client.post("/api/v1/portfolio/buy",
                      json={"symbol": "NICA", "quantity": 20}, headers=headers)

    # Price rises to 450 before selling 10.
    async with app.state.test_session() as s:
        from sqlalchemy import select
        stock_id = (await s.execute(select(Stock.id).where(Stock.symbol == "NICA"))).scalar_one()
        s.add(MarketData(stock_id=stock_id, open_price=450, high_price=450,
                         low_price=450, close_price=450, volume=1000,
                         timestamp=datetime.now(timezone.utc)))
        await s.commit()

    r = await client.post("/api/v1/portfolio/sell",
                          json={"symbol": "NICA", "quantity": 10}, headers=headers)
    assert r.status_code == 201, r.text
    # realized = (450-400)*10 - fee(450*10*0.004=18) = 500 - 18 = 482
    assert r.json()["realized_pnl"] == 482.0

    analytics = (await client.get("/api/v1/portfolio/analytics", headers=headers)).json()
    assert analytics["win_trades"] == 1
    assert analytics["loss_trades"] == 0
    assert 0 <= analytics["risk"]["score"] <= 100
    assert analytics["total_trades"] == 2  # 1 buy + 1 sell


async def test_sell_more_than_held_rejected(client):
    headers = await _auth(client)
    await _seed_stock("UPPER", 290.0)
    r = await client.post("/api/v1/portfolio/sell",
                          json={"symbol": "UPPER", "quantity": 5}, headers=headers)
    assert r.status_code == 400


async def test_risk_summary_degrades_without_ml(client):
    """risk-summary returns valid structure even when the ML service is down."""
    headers = await _auth(client)
    await _seed_stock("NABIL", 500.0)
    await client.post("/api/v1/portfolio/buy",
                      json={"symbol": "NABIL", "quantity": 10}, headers=headers)

    r = await client.get("/api/v1/portfolio/risk-summary", headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "portfolio_risk_score" in body
    assert isinstance(body["high_risk_holdings"], list)
    assert isinstance(body["warnings"], list) and body["warnings"]
