"""Portfolio + order-simulation engine.

The order engine validates trades, executes at the current market price with a
configurable fee, maintains average cost / realized P/L, and records an
immutable transaction. All monetary state lives on the portfolio + holdings.
"""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.config import settings
from portfolio.models import Holding, Portfolio, Transaction, TradeSide
from portfolio.pricing import get_price
from portfolio.services import risk_engine
from stocks.models import Stock
from stocks.service import get_by_symbol


# --------------------------------------------------------------------------- #
# Portfolio lifecycle
# --------------------------------------------------------------------------- #
async def get_or_create_default(db: AsyncSession, user_id: int) -> Portfolio:
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.id)
    )
    portfolio = result.scalars().first()
    if portfolio is None:
        portfolio = Portfolio(
            user_id=user_id,
            name="Default",
            initial_balance=settings.PORTFOLIO_INITIAL_BALANCE,
            cash_balance=settings.PORTFOLIO_INITIAL_BALANCE,
        )
        db.add(portfolio)
        await db.flush()
        await db.refresh(portfolio)
    return portfolio


async def resolve_portfolio(
    db: AsyncSession, user_id: int, portfolio_id: int | None
) -> Portfolio:
    if portfolio_id is None:
        return await get_or_create_default(db, user_id)
    portfolio = await db.get(Portfolio, portfolio_id)
    if portfolio is None or portfolio.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Portfolio not found"
        )
    return portfolio


async def list_portfolios(db: AsyncSession, user_id: int) -> list[Portfolio]:
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == user_id).order_by(Portfolio.id)
    )
    return list(result.scalars().all())


async def create_portfolio(db: AsyncSession, user_id: int, name: str) -> Portfolio:
    portfolio = Portfolio(
        user_id=user_id,
        name=name or "Portfolio",
        initial_balance=settings.PORTFOLIO_INITIAL_BALANCE,
        cash_balance=settings.PORTFOLIO_INITIAL_BALANCE,
    )
    db.add(portfolio)
    await db.flush()
    await db.refresh(portfolio)
    return portfolio


# --------------------------------------------------------------------------- #
# Order engine
# --------------------------------------------------------------------------- #
async def _get_stock(db: AsyncSession, symbol: str) -> Stock:
    stock = await get_by_symbol(db, symbol)
    if stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown symbol {symbol}"
        )
    return stock


async def _get_holding(db: AsyncSession, portfolio_id: int, stock_id: int) -> Holding | None:
    result = await db.execute(
        select(Holding).where(
            Holding.portfolio_id == portfolio_id, Holding.stock_id == stock_id
        )
    )
    return result.scalar_one_or_none()


async def buy(
    db: AsyncSession, portfolio: Portfolio, symbol: str, quantity: int
) -> Transaction:
    stock = await _get_stock(db, symbol)
    price = await get_price(db, stock)
    gross = price * quantity
    fee = round(gross * settings.PORTFOLIO_FEE_RATE, 2)
    cost = gross + fee

    if cost > portfolio.cash_balance + 1e-6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Insufficient funds: need {cost:.2f}, "
                f"have {portfolio.cash_balance:.2f}"
            ),
        )

    holding = await _get_holding(db, portfolio.id, stock.id)
    if holding is None:
        holding = Holding(portfolio_id=portfolio.id, stock_id=stock.id)
        db.add(holding)
        await db.flush()

    # Weighted-average cost.
    total_qty = holding.quantity + quantity
    holding.avg_buy_price = (
        holding.quantity * holding.avg_buy_price + gross
    ) / total_qty
    holding.quantity = total_qty
    portfolio.cash_balance = round(portfolio.cash_balance - cost, 2)

    txn = Transaction(
        portfolio_id=portfolio.id, stock_id=stock.id, side=TradeSide.BUY,
        quantity=quantity, price=price, fee=fee, total_value=round(gross, 2),
    )
    db.add(txn)
    await db.flush()
    await db.refresh(txn)
    return txn


async def sell(
    db: AsyncSession, portfolio: Portfolio, symbol: str, quantity: int
) -> Transaction:
    stock = await _get_stock(db, symbol)
    holding = await _get_holding(db, portfolio.id, stock.id)
    if holding is None or holding.quantity < quantity:
        held = holding.quantity if holding else 0
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient holdings: trying to sell {quantity}, hold {held}",
        )

    price = await get_price(db, stock)
    gross = price * quantity
    fee = round(gross * settings.PORTFOLIO_FEE_RATE, 2)
    proceeds = gross - fee
    realized = round((price - holding.avg_buy_price) * quantity - fee, 2)

    holding.quantity -= quantity
    holding.realized_pnl = round(holding.realized_pnl + realized, 2)
    if holding.quantity == 0:
        holding.avg_buy_price = 0.0
    portfolio.cash_balance = round(portfolio.cash_balance + proceeds, 2)

    txn = Transaction(
        portfolio_id=portfolio.id, stock_id=stock.id, side=TradeSide.SELL,
        quantity=quantity, price=price, fee=fee, total_value=round(gross, 2),
        realized_pnl=realized,
    )
    db.add(txn)
    await db.flush()
    await db.refresh(txn)
    return txn


# --------------------------------------------------------------------------- #
# Valuation
# --------------------------------------------------------------------------- #
async def build_summary(
    db: AsyncSession, portfolio: Portfolio, auth_token: str | None = None
) -> dict:
    result = await db.execute(
        select(Holding)
        .where(Holding.portfolio_id == portfolio.id, Holding.quantity > 0)
        .options(selectinload(Holding.stock))
    )
    holdings = list(result.scalars().all())

    # Batch-fetch ML risk for all held symbols (cached; fails soft to {}).
    risk_map = await risk_engine.get_batch(
        [h.stock.symbol for h in holdings], auth_token
    )

    rows: list[dict] = []
    holdings_value = 0.0
    unrealized_total = 0.0
    for h in holdings:
        price = await get_price(db, h.stock)
        market_value = price * h.quantity
        cost_basis = h.avg_buy_price * h.quantity
        unrealized = market_value - cost_basis
        holdings_value += market_value
        unrealized_total += unrealized
        risk = risk_map.get(h.stock.symbol.upper())
        rows.append(
            {
                "symbol": h.stock.symbol,
                "company_name": h.stock.company_name,
                "sector": h.stock.sector,
                "quantity": h.quantity,
                "avg_buy_price": round(h.avg_buy_price, 2),
                "current_price": round(price, 2),
                "market_value": round(market_value, 2),
                "cost_basis": round(cost_basis, 2),
                "unrealized_pnl": round(unrealized, 2),
                "unrealized_pct": round((unrealized / cost_basis * 100) if cost_basis else 0.0, 2),
                "realized_pnl": round(h.realized_pnl, 2),
                "risk": risk,
            }
        )

    realized_total = await _total_realized(db, portfolio.id)
    total_value = portfolio.cash_balance + holdings_value
    total_pnl = total_value - portfolio.initial_balance
    roi = (total_pnl / portfolio.initial_balance * 100) if portfolio.initial_balance else 0.0

    return {
        "portfolio_id": portfolio.id,
        "name": portfolio.name,
        "initial_balance": round(portfolio.initial_balance, 2),
        "cash_balance": round(portfolio.cash_balance, 2),
        "holdings_value": round(holdings_value, 2),
        "total_value": round(total_value, 2),
        "total_unrealized_pnl": round(unrealized_total, 2),
        "total_realized_pnl": round(realized_total, 2),
        "total_pnl": round(total_pnl, 2),
        "roi": round(roi, 2),
        "holdings": rows,
    }


async def _total_realized(db: AsyncSession, portfolio_id: int) -> float:
    result = await db.execute(
        select(Holding.realized_pnl).where(Holding.portfolio_id == portfolio_id)
    )
    return float(sum(result.scalars().all()))


async def list_transactions(
    db: AsyncSession,
    portfolio_id: int,
    symbol: str | None = None,
    side: TradeSide | None = None,
    limit: int = 200,
) -> list[dict]:
    stmt = (
        select(Transaction)
        .where(Transaction.portfolio_id == portfolio_id)
        .options(selectinload(Transaction.stock))
        .order_by(Transaction.timestamp.desc())
    )
    if side:
        stmt = stmt.where(Transaction.side == side)
    result = await db.execute(stmt.limit(limit))
    txns = list(result.scalars().all())
    out = []
    for t in txns:
        if symbol and t.stock.symbol.upper() != symbol.upper():
            continue
        out.append(
            {
                "id": t.id, "symbol": t.stock.symbol, "side": t.side,
                "quantity": t.quantity, "price": t.price, "fee": t.fee,
                "total_value": t.total_value, "realized_pnl": t.realized_pnl,
                "timestamp": t.timestamp,
            }
        )
    return out
