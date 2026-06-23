"""Portfolio API: trading, summary, transactions, analytics."""
from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_access_token, get_current_user
from core.database import get_db
from portfolio import analytics, service
from portfolio.models import TradeSide
from portfolio.schemas import (
    AnalyticsOut,
    PortfolioOut,
    PortfolioSummary,
    RiskSummaryOut,
    TradeRequest,
    TransactionOut,
)
from users.models import User

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("/buy", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def buy(
    payload: TradeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = await service.resolve_portfolio(db, user.id, payload.portfolio_id)
    txn = await service.buy(db, portfolio, payload.symbol, payload.quantity)
    return {"id": txn.id, "symbol": payload.symbol.upper(), "side": txn.side,
            "quantity": txn.quantity, "price": txn.price, "fee": txn.fee,
            "total_value": txn.total_value, "realized_pnl": txn.realized_pnl,
            "timestamp": txn.timestamp}


@router.post("/sell", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def sell(
    payload: TradeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = await service.resolve_portfolio(db, user.id, payload.portfolio_id)
    txn = await service.sell(db, portfolio, payload.symbol, payload.quantity)
    return {"id": txn.id, "symbol": payload.symbol.upper(), "side": txn.side,
            "quantity": txn.quantity, "price": txn.price, "fee": txn.fee,
            "total_value": txn.total_value, "realized_pnl": txn.realized_pnl,
            "timestamp": txn.timestamp}


@router.get("/summary", response_model=PortfolioSummary)
async def summary(
    portfolio_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    token: str = Depends(get_access_token),
):
    portfolio = await service.resolve_portfolio(db, user.id, portfolio_id)
    return await service.build_summary(db, portfolio, token)


@router.get("/transactions", response_model=list[TransactionOut])
async def transactions(
    portfolio_id: int | None = Query(None),
    symbol: str | None = Query(None),
    side: TradeSide | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolio = await service.resolve_portfolio(db, user.id, portfolio_id)
    return await service.list_transactions(db, portfolio.id, symbol, side, limit)


@router.get("/analytics", response_model=AnalyticsOut)
async def get_analytics(
    portfolio_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    token: str = Depends(get_access_token),
):
    portfolio = await service.resolve_portfolio(db, user.id, portfolio_id)
    return await analytics.build_analytics(db, portfolio, token)


@router.get("/risk-summary", response_model=RiskSummaryOut)
async def risk_summary(
    portfolio_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    token: str = Depends(get_access_token),
):
    portfolio = await service.resolve_portfolio(db, user.id, portfolio_id)
    return await analytics.build_risk_summary(db, portfolio, token)


# ---- multiple portfolios (optional advanced feature) ----
@router.get("", response_model=list[PortfolioOut])
async def list_portfolios(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    portfolios = await service.list_portfolios(db, user.id)
    if not portfolios:
        portfolios = [await service.get_or_create_default(db, user.id)]
    return portfolios


@router.post("", response_model=PortfolioOut, status_code=status.HTTP_201_CREATED)
async def create_portfolio(
    name: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.create_portfolio(db, user.id, name)
