"""Pydantic response schemas for the analytics API."""
from pydantic import BaseModel


class MarketOverview(BaseModel):
    index_value: float
    index_change_percent: float
    total_stocks: int
    advancers: int
    decliners: int
    unchanged: int
    total_volume: int
    total_turnover: float
    avg_change_percent: float
    sentiment: str
    sentiment_score: float


class SectorPerformance(BaseModel):
    sector: str
    stocks: int
    avg_change_percent: float
    advancers: int
    decliners: int
    total_volume: int
    total_turnover: float
    relative_strength: float


class Mover(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    turnover: float


class HeatmapTile(BaseModel):
    symbol: str
    sector: str
    change_percent: float
    price: float
    volume: int
    turnover: float
    weight: float


class IndicatorPoint(BaseModel):
    timestamp: str
    value: float | None


class TechnicalSignal(BaseModel):
    indicator: str
    signal: str
    note: str


class TechnicalResponse(BaseModel):
    symbol: str
    timeframe: str
    points: int
    latest: dict
    series: dict  # indicator -> list[{timestamp, value}]
    insights: list[str]
    suggestion: dict


class AIInsightResponse(BaseModel):
    scope: str  # "market" or a symbol
    insights: list[str]
    suggestion: dict | None = None
