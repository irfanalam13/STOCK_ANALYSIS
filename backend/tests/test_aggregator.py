"""Unit tests for market aggregation + AI insights (pure logic)."""
from analytics import aggregator as agg
from analytics import ai_insights


def _row(symbol, price, change_pct, volume):
    return {
        "symbol": symbol, "price": price,
        "change": round(price * change_pct / 100, 2),
        "change_percent": change_pct, "volume": volume,
        "timestamp": "2026-06-20T10:00:00+00:00",
    }


ROWS = [
    _row("NABIL", 500, 2.0, 10_000),   # bank, up
    _row("NICA", 400, 1.0, 5_000),     # bank, up
    _row("UPPER", 300, -3.0, 20_000),  # hydro, down
    _row("CHCL", 470, -1.0, 1_000),    # hydro, down
    _row("NTC", 980, 0.0, 2_000),      # telecom, flat
]
SECTORS = {"NABIL": "Bank", "NICA": "Bank", "UPPER": "Hydro",
           "CHCL": "Hydro", "NTC": "Telecom"}


def test_overview_breadth_and_fields():
    o = agg.compute_overview(ROWS, 2000.0)
    assert o["total_stocks"] == 5
    assert o["advancers"] == 2 and o["decliners"] == 2 and o["unchanged"] == 1
    assert o["total_volume"] == 38_000
    assert o["sentiment"] in {"Bullish", "Bearish", "Neutral"}
    assert 0 <= o["sentiment_score"] <= 100


def test_overview_empty():
    o = agg.compute_overview([], 2000.0)
    assert o["total_stocks"] == 0 and o["sentiment"] == "Neutral"
    assert o["index_value"] == 2000.0


def test_sectors_grouping_and_sort():
    s = agg.compute_sectors(ROWS, SECTORS)
    sectors = {row["sector"]: row for row in s}
    assert sectors["Bank"]["stocks"] == 2
    assert sectors["Bank"]["avg_change_percent"] == 1.5
    # Sorted strongest first.
    assert s[0]["avg_change_percent"] >= s[-1]["avg_change_percent"]
    # Relative strength is measured against the market average.
    assert sectors["Bank"]["relative_strength"] > 0


def test_rank_movers_gainers_and_losers():
    gainers = agg.rank_movers(ROWS, "gainers", top=2)
    assert [g["symbol"] for g in gainers] == ["NABIL", "NICA"]
    losers = agg.rank_movers(ROWS, "losers", top=2)
    assert [l["symbol"] for l in losers] == ["UPPER", "CHCL"]


def test_rank_movers_min_volume_filter():
    gainers = agg.rank_movers(ROWS, "gainers", top=10, min_volume=6_000)
    # Only NABIL (10k) and UPPER (20k) clear the 6k volume floor; ranked desc.
    assert [g["symbol"] for g in gainers] == ["NABIL", "UPPER"]
    # Low-liquidity names (NICA 5k, CHCL 1k, NTC 2k) are filtered out.
    assert all(g["volume"] >= 6_000 for g in gainers)


def test_heatmap_volume_weights_sum_to_one():
    tiles = agg.build_heatmap(ROWS, SECTORS, mode="volume")
    assert abs(sum(t["weight"] for t in tiles) - 1.0) < 1e-6
    assert all("sector" in t for t in tiles)


def test_market_insights_returns_text():
    o = agg.compute_overview(ROWS, 2000.0)
    s = agg.compute_sectors(ROWS, SECTORS)
    msgs = ai_insights.market_insights(o, s)
    assert msgs and all(isinstance(m, str) for m in msgs)


def test_suggestion_buy_on_oversold_bullish():
    ind = {"rsi": 25, "macd_histogram": 0.5, "price": 110, "sma_50": 100}
    out = ai_insights.suggestion(ind)
    assert out["action"] == "BUY" and 0 <= out["confidence"] <= 1


def test_suggestion_sell_on_overbought_bearish():
    ind = {"rsi": 80, "macd_histogram": -0.5, "price": 90, "sma_50": 100}
    assert ai_insights.suggestion(ind)["action"] == "SELL"


def test_suggestion_hold_without_data():
    assert ai_insights.suggestion({})["action"] == "HOLD"
