"""Unit tests for the portfolio risk-engine adapter."""
import pytest

from portfolio.services import risk_engine

pytestmark = pytest.mark.asyncio


def test_normalize_sell_signal_raises_risk():
    out = risk_engine._normalize(
        {"symbol": "nabil", "volatility_score": 0.6, "signal": "SELL", "confidence": 0.7}
    )
    # 0.6 vol + 0.3 SELL impact = 0.9 -> HIGH
    assert out["symbol"] == "NABIL"
    assert out["risk_level"] == "HIGH"
    assert out["trend_signal"] == "SELL"


def test_normalize_buy_signal_lowers_risk():
    out = risk_engine._normalize(
        {"symbol": "NICA", "volatility_score": 0.4, "signal": "BUY", "confidence": 0.6}
    )
    # 0.4 - 0.2 = 0.2 -> LOW
    assert out["risk_level"] == "LOW"


async def test_get_batch_normalizes_ml_response(monkeypatch):
    async def fake_call(symbols, token):
        return [
            {"symbol": s, "volatility_score": 0.8, "signal": "SELL", "confidence": 0.7}
            for s in symbols
        ]

    monkeypatch.setattr(risk_engine, "_call_ml", fake_call)
    result = await risk_engine.get_batch(["NABIL"], auth_token="t")
    assert result["NABIL"]["risk_level"] == "HIGH"
    assert result["NABIL"]["volatility_score"] == 0.8


async def test_get_batch_empty_symbols():
    assert await risk_engine.get_batch([], None) == {}
