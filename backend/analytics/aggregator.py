"""Pure market-aggregation logic.

Operates on a list of live snapshot rows (the per-symbol payload the broadcast
stage caches) plus a ``symbol -> sector`` map. No I/O — so it is reused by the
async API service and the synchronous Celery precompute task, and is directly
unit-testable.

Row shape (from ``market:snapshot``):
    {"symbol", "price", "change", "change_percent", "volume", "timestamp"}

Note on market cap: NEPSE listed-share counts aren't in our dataset, so a true
market cap can't be computed. We use **turnover** (price × volume) as the
liquidity/size proxy and a turnover-weighted index level.
"""
from __future__ import annotations

Row = dict
SectorMap = dict[str, str | None]


def _turnover(r: Row) -> float:
    return float(r["price"]) * float(r["volume"])


def compute_overview(rows: list[Row], index_base: float = 2000.0) -> dict:
    """Index proxy, breadth, volume/turnover, and a market sentiment score."""
    if not rows:
        return {
            "index_value": index_base, "index_change_percent": 0.0,
            "total_stocks": 0, "advancers": 0, "decliners": 0, "unchanged": 0,
            "total_volume": 0, "total_turnover": 0.0, "avg_change_percent": 0.0,
            "sentiment": "Neutral", "sentiment_score": 50.0,
        }

    advancers = sum(1 for r in rows if r["change_percent"] > 0)
    decliners = sum(1 for r in rows if r["change_percent"] < 0)
    unchanged = len(rows) - advancers - decliners
    total_volume = sum(int(r["volume"]) for r in rows)
    total_turnover = sum(_turnover(r) for r in rows)
    avg_change = sum(r["change_percent"] for r in rows) / len(rows)

    # Turnover-weighted change is a closer analogue to a value-weighted index.
    weighted_change = (
        sum(r["change_percent"] * _turnover(r) for r in rows) / total_turnover
        if total_turnover > 0 else avg_change
    )
    index_value = index_base * (1 + weighted_change / 100)

    label, score = _sentiment(advancers, decliners, len(rows), weighted_change)
    return {
        "index_value": round(index_value, 2),
        "index_change_percent": round(weighted_change, 2),
        "total_stocks": len(rows),
        "advancers": advancers,
        "decliners": decliners,
        "unchanged": unchanged,
        "total_volume": total_volume,
        "total_turnover": round(total_turnover, 2),
        "avg_change_percent": round(avg_change, 2),
        "sentiment": label,
        "sentiment_score": score,
    }


def _sentiment(adv: int, dec: int, total: int, weighted_change: float) -> tuple[str, float]:
    """Blend breadth and turnover-weighted change into a 0-100 score."""
    breadth = (adv - dec) / total if total else 0.0  # -1..1
    # Map weighted change (≈ -10%..+10%) to -1..1 and average with breadth.
    momentum = max(-1.0, min(1.0, weighted_change / 3.0))
    score = round(50 + (breadth * 0.5 + momentum * 0.5) * 50, 1)
    score = max(0.0, min(100.0, score))
    if score >= 60:
        label = "Bullish"
    elif score <= 40:
        label = "Bearish"
    else:
        label = "Neutral"
    return label, score


def compute_sectors(rows: list[Row], sector_map: SectorMap) -> list[dict]:
    """Per-sector performance, sorted strongest first, with relative strength."""
    buckets: dict[str, list[Row]] = {}
    for r in rows:
        sector = sector_map.get(r["symbol"]) or "Unclassified"
        buckets.setdefault(sector, []).append(r)

    market_avg = (
        sum(r["change_percent"] for r in rows) / len(rows) if rows else 0.0
    )

    sectors: list[dict] = []
    for sector, members in buckets.items():
        avg_change = sum(m["change_percent"] for m in members) / len(members)
        sectors.append({
            "sector": sector,
            "stocks": len(members),
            "avg_change_percent": round(avg_change, 2),
            "advancers": sum(1 for m in members if m["change_percent"] > 0),
            "decliners": sum(1 for m in members if m["change_percent"] < 0),
            "total_volume": sum(int(m["volume"]) for m in members),
            "total_turnover": round(sum(_turnover(m) for m in members), 2),
            # Relative strength vs the whole market (>0 = outperforming).
            "relative_strength": round(avg_change - market_avg, 2),
        })
    sectors.sort(key=lambda s: s["avg_change_percent"], reverse=True)
    return sectors


def rank_movers(
    rows: list[Row], direction: str = "gainers", top: int = 10, min_volume: int = 0
) -> list[dict]:
    """Top gainers/losers, liquidity-aware via a minimum-volume filter."""
    eligible = [r for r in rows if int(r["volume"]) >= min_volume]
    reverse = direction == "gainers"
    ordered = sorted(eligible, key=lambda r: r["change_percent"], reverse=reverse)
    return [
        {
            "symbol": r["symbol"],
            "price": round(float(r["price"]), 2),
            "change": round(float(r["change"]), 2),
            "change_percent": round(float(r["change_percent"]), 2),
            "volume": int(r["volume"]),
            "turnover": round(_turnover(r), 2),
        }
        for r in ordered[:top]
    ]


def build_heatmap(
    rows: list[Row], sector_map: SectorMap, mode: str = "change"
) -> list[dict]:
    """Heatmap tiles grouped by sector.

    ``mode='change'`` sizes tiles equally; ``mode='volume'`` sizes by turnover
    so liquid names dominate the map.
    """
    total_turnover = sum(_turnover(r) for r in rows) or 1.0
    tiles: list[dict] = []
    for r in rows:
        turnover = _turnover(r)
        weight = (turnover / total_turnover) if mode == "volume" else (1.0 / len(rows))
        tiles.append({
            "symbol": r["symbol"],
            "sector": sector_map.get(r["symbol"]) or "Unclassified",
            "change_percent": round(float(r["change_percent"]), 2),
            "price": round(float(r["price"]), 2),
            "volume": int(r["volume"]),
            "turnover": round(turnover, 2),
            "weight": round(weight, 6),
        })
    tiles.sort(key=lambda t: (t["sector"], -t["change_percent"]))
    return tiles
