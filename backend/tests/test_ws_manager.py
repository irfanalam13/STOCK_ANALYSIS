"""Unit tests for the channel-based WebSocket routing engine."""
import json

import pytest

from websocket.manager import ConnectionManager

pytestmark = pytest.mark.asyncio


class FakeWS:
    """Minimal async WebSocket double that records sent frames."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def accept(self) -> None:  # noqa: D401
        pass

    async def send_text(self, payload: str) -> None:
        self.sent.append(json.loads(payload))

    def messages(self, kind: str) -> list[dict]:
        return [m for m in self.sent if m.get("type") == kind]


PRICES = [
    {"symbol": "NABIL", "price": 542.5, "change": 12.5, "change_percent": 2.3, "volume": 100, "timestamp": "t"},
    {"symbol": "NICA", "price": 410.0, "change": -2.0, "change_percent": -0.5, "volume": 200, "timestamp": "t"},
]


async def test_per_symbol_subscriber_gets_only_its_symbol():
    mgr = ConnectionManager()
    ws = FakeWS()
    cid = await mgr.connect(ws)
    await mgr.subscribe(cid, ["NABIL"])

    await mgr.route_prices(1, PRICES)

    price_msgs = ws.messages("prices")
    assert len(price_msgs) == 1
    data = price_msgs[0]["data"]
    assert [d["symbol"] for d in data] == ["NABIL"]
    assert price_msgs[0]["seq"] == 1


async def test_ticker_subscriber_gets_full_batch():
    mgr = ConnectionManager()
    ws = FakeWS()
    cid = await mgr.connect(ws)
    await mgr.subscribe_ticker(cid)

    await mgr.route_prices(7, PRICES)

    data = ws.messages("prices")[0]["data"]
    assert {d["symbol"] for d in data} == {"NABIL", "NICA"}


async def test_unsubscribe_and_disconnect_clean_up():
    mgr = ConnectionManager()
    ws = FakeWS()
    cid = await mgr.connect(ws)
    await mgr.subscribe(cid, ["NABIL"])
    await mgr.unsubscribe(cid, ["NABIL"])

    await mgr.route_prices(1, PRICES)
    assert ws.messages("prices") == []  # no longer subscribed

    await mgr.disconnect(cid)
    assert mgr.connection_count == 0


async def test_ohlc_routes_to_symbol_subscriber_only():
    mgr = ConnectionManager()
    sub, other = FakeWS(), FakeWS()
    sub_id = await mgr.connect(sub)
    other_id = await mgr.connect(other)
    await mgr.subscribe(sub_id, ["NABIL"])
    await mgr.subscribe(other_id, ["NICA"])

    await mgr.route_ohlc(
        3, [{"symbol": "NABIL", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 5, "interval": "1m", "timestamp": "t"}]
    )

    assert len(sub.messages("ohlc")) == 1
    assert other.messages("ohlc") == []
