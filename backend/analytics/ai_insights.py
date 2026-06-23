"""Rule-based AI insights layer.

Turns computed numbers (overview, sector strength, per-symbol indicators) into
plain-language interpretations and a probabilistic Buy/Sell/Hold suggestion.
It is deterministic, dependency-free, and fast (<1ms) — meeting the phase's
<500ms response target without a heavyweight model — while leaving a clean seam
to swap in an ML classifier later.

Nothing here is financial advice; suggestions are confidence-scored heuristics.
"""
from __future__ import annotations


def market_insights(overview: dict, sectors: list[dict]) -> list[str]:
    """Headline narrative for the whole market."""
    out: list[str] = []
    sentiment = overview.get("sentiment", "Neutral")
    chg = overview.get("index_change_percent", 0.0)
    adv = overview.get("advancers", 0)
    dec = overview.get("decliners", 0)

    if sectors:
        leader = sectors[0]
        if sentiment == "Bullish" and leader["avg_change_percent"] > 0:
            out.append(
                f"Market is showing bullish momentum, led by {leader['sector']} "
                f"({leader['avg_change_percent']:+.2f}%)."
            )
        elif sentiment == "Bearish":
            laggard = sectors[-1]
            out.append(
                f"Market is under pressure ({chg:+.2f}%), dragged by "
                f"{laggard['sector']} ({laggard['avg_change_percent']:+.2f}%)."
            )
        else:
            out.append(
                f"Market is broadly neutral ({chg:+.2f}%); {leader['sector']} "
                f"is the relative outperformer."
            )

    out.append(
        f"Breadth: {adv} advancing vs {dec} declining — "
        f"{'positive' if adv > dec else 'negative' if dec > adv else 'balanced'} participation."
    )

    strong = [s for s in sectors if s["relative_strength"] > 1.0]
    if strong:
        names = ", ".join(s["sector"] for s in strong[:3])
        out.append(f"Sector strength concentrated in {names}.")
    return out


def technical_insights(symbol: str, ind: dict) -> list[str]:
    """Per-symbol indicator interpretation in natural language."""
    out: list[str] = []
    rsi = ind.get("rsi")
    hist = ind.get("macd_histogram")
    price = ind.get("price")
    sma50 = ind.get("sma_50")

    if rsi is not None:
        if rsi >= 70:
            out.append(f"RSI at {rsi:.0f} indicates {symbol} is overbought — pullback risk.")
        elif rsi <= 30:
            out.append(f"RSI at {rsi:.0f} indicates {symbol} is oversold — possible bounce.")
        else:
            out.append(f"RSI at {rsi:.0f} is neutral for {symbol}.")
    if hist is not None:
        if hist > 0:
            out.append(f"MACD crossover suggests a potential upward trend in {symbol}.")
        elif hist < 0:
            out.append(f"MACD is below its signal line — bearish bias for {symbol}.")
    if price is not None and sma50 is not None:
        if price > sma50:
            out.append(f"{symbol} trades above its 50-period average — uptrend intact.")
        else:
            out.append(f"{symbol} trades below its 50-period average — downtrend bias.")
    return out


def suggestion(ind: dict) -> dict:
    """Probabilistic Buy/Sell/Hold from a weighted blend of signals.

    Returns ``{action, confidence, rationale}``. Confidence is the share of the
    evidence pointing the chosen way — never presented as certainty.
    """
    score = 0.0
    weight = 0.0
    rationale: list[str] = []

    rsi = ind.get("rsi")
    if rsi is not None:
        weight += 1
        if rsi <= 30:
            score += 1; rationale.append("RSI oversold")
        elif rsi >= 70:
            score -= 1; rationale.append("RSI overbought")

    hist = ind.get("macd_histogram")
    if hist is not None:
        weight += 1
        if hist > 0:
            score += 1; rationale.append("MACD bullish")
        elif hist < 0:
            score -= 1; rationale.append("MACD bearish")

    price, sma50 = ind.get("price"), ind.get("sma_50")
    if price is not None and sma50 is not None:
        weight += 1
        if price > sma50:
            score += 1; rationale.append("above SMA50")
        else:
            score -= 1; rationale.append("below SMA50")

    if weight == 0:
        return {"action": "HOLD", "confidence": 0.0,
                "rationale": "insufficient data"}

    norm = score / weight  # -1..1
    if norm > 0.33:
        action = "BUY"
    elif norm < -0.33:
        action = "SELL"
    else:
        action = "HOLD"
    confidence = round(abs(norm), 2)
    return {
        "action": action,
        "confidence": confidence,
        "rationale": ", ".join(rationale) or "mixed signals",
    }
