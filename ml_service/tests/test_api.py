"""API tests — auth enforcement + response shapes (works in fallback mode)."""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt

from config import settings

pytestmark = pytest.mark.asyncio


def _token() -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": "1", "type": "access", "role": "trader",
         "iat": now, "exp": now + timedelta(hours=1)},
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


@pytest.fixture
async def client():
    from app import _state, app
    from models.service import ModelService

    _state["service"] = ModelService()  # lifespan isn't run by ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_requires_auth(client):
    r = await client.post("/predict/price", json={"symbol": "NABIL"})
    assert r.status_code == 401


async def test_predict_price_shape(client):
    r = await client.post(
        "/predict/price",
        headers={"Authorization": f"Bearer {_token()}"},
        json={"symbol": "NABIL", "features": {
            "open": 520, "high": 530, "low": 515, "close": 525, "volume": 120000}},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["symbol"] == "NABIL"
    assert body["predicted_price"] > 0
    assert 0 <= body["confidence"] <= 1


async def test_signal_shape(client):
    r = await client.post(
        "/signal/stock",
        headers={"Authorization": f"Bearer {_token()}"},
        json={"symbol": "NABIL"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["signal"] in {"BUY", "SELL", "HOLD"}
    assert body["strength"] in {"STRONG", "MODERATE", "WEAK", "NEUTRAL"}
    assert isinstance(body["reason"], list)
