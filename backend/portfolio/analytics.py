"""Portfolio analytics: ROI, win/loss, asset allocation, and a risk score.

Risk score (0 = low, 100 = high) blends three intuitive factors:
  * concentration — Herfindahl index of holding weights (all-in-one ≈ 1.0)
  * diversification — more sectors lowers risk (up to a cap)
  * exposure — cash on the sidelines lowers risk
"""
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from portfolio.models import Portfolio, Transaction, TradeSide
from portfolio import service


async def build_analytics(
    db: AsyncSession, portfolio: Portfolio, auth_token: str | None = None
) -> dict:
    summary = await service.build_summary(db, portfolio, auth_token)
    holdings = summary["holdings"]
    total_value = summary["total_value"]
    invested = summary["holdings_value"]

    # ---- win / loss from realized sell transactions ----
    result = await db.execute(
        select(Transaction.realized_pnl).where(
            Transaction.portfolio_id == portfolio.id,
            Transaction.side == TradeSide.SELL,
        )
    )
    realized = [r for r in result.scalars().all() if r is not None]
    wins = sum(1 for r in realized if r > 0)
    losses = sum(1 for r in realized if r < 0)
    win_loss_ratio = round(wins / losses, 2) if losses else float(wins)

    total_trades_result = await db.execute(
        select(Transaction.id).where(Transaction.portfolio_id == portfolio.id)
    )
    total_trades = len(total_trades_result.scalars().all())

    # ---- asset allocation by sector (+ cash) ----
    by_sector: dict[str, float] = defaultdict(float)
    for h in holdings:
        by_sector[h["sector"] or "Other"] += h["market_value"]
    allocation = [
        {"label": sector, "value": round(value, 2),
         "pct": round(value / total_value * 100, 2) if total_value else 0.0}
        for sector, value in sorted(by_sector.items(), key=lambda kv: -kv[1])
    ]
    if summary["cash_balance"] > 0 and total_value:
        allocation.append(
            {"label": "Cash", "value": round(summary["cash_balance"], 2),
             "pct": round(summary["cash_balance"] / total_value * 100, 2)}
        )

    # ---- risk score ----
    risk = _risk_score(holdings, invested, summary["cash_balance"], total_value)

    return {
        "portfolio_id": portfolio.id,
        "roi": summary["roi"],
        "total_value": total_value,
        "invested": round(invested, 2),
        "total_pnl": summary["total_pnl"],
        "total_trades": total_trades,
        "win_trades": wins,
        "loss_trades": losses,
        "win_loss_ratio": win_loss_ratio,
        "allocation": allocation,
        "risk": risk,
    }


# Signal → additive risk impact (per spec ML signal mapping), normalized to 0..1.
_SIGNAL_IMPACT = {"BUY": -0.2, "HOLD": 0.0, "SELL": 0.3}


def _risk_score(holdings, invested, cash, total_value) -> dict:
    if invested <= 0 or not holdings:
        return {"score": 0.0, "concentration": 0.0, "sectors": 0, "exposure": 0.0}

    weights = [h["market_value"] / invested for h in holdings]
    hhi = sum(w * w for w in weights)  # 1/n .. 1  (concentration risk)
    sectors = len({h["sector"] or "Other" for h in holdings})
    exposure = invested / total_value if total_value else 0.0

    # ML-derived components (value-weighted). Present only when risk data exists.
    have_ml = any(h.get("risk") for h in holdings)
    if have_ml:
        volatility_risk = sum(
            w * float((h.get("risk") or {}).get("volatility_score", 0.0))
            for w, h in zip(weights, holdings)
        )
        signal_norm = sum(
            w * ((_SIGNAL_IMPACT.get((h.get("risk") or {}).get("trend_signal", "HOLD"), 0.0) + 0.2) / 0.5)
            for w, h in zip(weights, holdings)
        )
        # Weighted blend (per spec): concentration .35, volatility .25,
        # exposure .20, ML signal .20.
        score = 100 * (
            0.35 * hhi
            + 0.25 * volatility_risk
            + 0.20 * exposure
            + 0.20 * signal_norm
        )
    else:
        # No ML data — fall back to the structural heuristic.
        diversification_mult = 1 - min(0.5, 0.1 * (sectors - 1))
        score = 100 * hhi * diversification_mult * exposure

    return {
        "score": round(min(100.0, max(0.0, score)), 1),
        "concentration": round(hhi, 3),
        "sectors": sectors,
        "exposure": round(exposure, 3),
    }


async def build_risk_summary(
    db: AsyncSession, portfolio: Portfolio, auth_token: str | None = None
) -> dict:
    """High-level risk panel: overall score, risky holdings, and warnings."""
    summary = await service.build_summary(db, portfolio, auth_token)
    holdings = summary["holdings"]

    risk = _risk_score(
        holdings, summary["holdings_value"], summary["cash_balance"],
        summary["total_value"],
    )
    high_risk = [
        h["symbol"] for h in holdings
        if (h.get("risk") or {}).get("risk_level") == "HIGH"
    ]

    warnings: list[str] = []
    # Sector concentration warning (>40% in one sector).
    by_sector: dict[str, float] = defaultdict(float)
    for h in holdings:
        by_sector[h["sector"] or "Other"] += h["market_value"]
    if summary["holdings_value"] > 0:
        for sector, value in by_sector.items():
            if value / summary["holdings_value"] > 0.40:
                warnings.append(f"High concentration in {sector} sector")
    if high_risk:
        warnings.append(
            f"{len(high_risk)} asset(s) show elevated volatility: {', '.join(high_risk)}"
        )
    if risk["score"] >= 66:
        warnings.append("Overall portfolio risk is HIGH")
    if summary["total_value"] > 0 and summary["cash_balance"] / summary["total_value"] < 0.05:
        warnings.append("Low cash buffer — limited flexibility")
    if not warnings:
        warnings.append("No significant risks detected")

    return {
        "portfolio_id": portfolio.id,
        "portfolio_risk_score": risk["score"],
        "high_risk_holdings": high_risk,
        "warnings": warnings,
    }
