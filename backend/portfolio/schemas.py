"""Pydantic schemas for the portfolio system."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from portfolio.models import TradeSide


class TradeRequest(BaseModel):
    symbol: str
    quantity: int = Field(gt=0)
    portfolio_id: int | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    side: TradeSide
    quantity: int
    price: float
    fee: float
    total_value: float
    realized_pnl: float | None
    timestamp: datetime


class HoldingRisk(BaseModel):
    volatility_score: float
    trend_signal: str
    risk_level: str
    confidence: float


class HoldingOut(BaseModel):
    symbol: str
    company_name: str
    sector: str | None
    quantity: int
    avg_buy_price: float
    current_price: float
    market_value: float
    cost_basis: float
    unrealized_pnl: float
    unrealized_pct: float
    realized_pnl: float
    risk: HoldingRisk | None = None


class PortfolioSummary(BaseModel):
    portfolio_id: int
    name: str
    initial_balance: float
    cash_balance: float
    holdings_value: float
    total_value: float
    total_unrealized_pnl: float
    total_realized_pnl: float
    total_pnl: float
    roi: float
    holdings: list[HoldingOut]


class AllocationSlice(BaseModel):
    label: str
    value: float
    pct: float


class RiskScore(BaseModel):
    score: float
    concentration: float
    sectors: int
    exposure: float


class AnalyticsOut(BaseModel):
    portfolio_id: int
    roi: float
    total_value: float
    invested: float
    total_pnl: float
    total_trades: int
    win_trades: int
    loss_trades: int
    win_loss_ratio: float
    allocation: list[AllocationSlice]
    risk: RiskScore


class RiskSummaryOut(BaseModel):
    portfolio_id: int
    portfolio_risk_score: float
    high_risk_holdings: list[str]
    warnings: list[str]


class PortfolioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    initial_balance: float
    cash_balance: float
    created_at: datetime
