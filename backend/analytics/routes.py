"""Analytics dashboard API (Phase 7).

All routes require authentication. Live aggregations are cached for sub-second
loads; technical indicators are computed per symbol+timeframe.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from analytics import ai_insights, service, technical
from analytics.schemas import (
    AIInsightResponse,
    HeatmapTile,
    MarketOverview,
    Mover,
    SectorPerformance,
    TechnicalResponse,
)
from auth.dependencies import get_current_user
from core.database import get_db
from users.models import User

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=MarketOverview)
async def market_overview(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.overview(db)


@router.get("/sectors", response_model=list[SectorPerformance])
async def sector_performance(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.sectors(db)


@router.get("/gainers", response_model=list[Mover])
async def top_gainers(
    top: int = Query(10, ge=1, le=50),
    min_volume: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.movers(db, "gainers", top, min_volume)


@router.get("/losers", response_model=list[Mover])
async def top_losers(
    top: int = Query(10, ge=1, le=50),
    min_volume: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.movers(db, "losers", top, min_volume)


@router.get("/heatmap", response_model=list[HeatmapTile])
async def market_heatmap(
    mode: str = Query("change", pattern="^(change|volume)$"),
    sector: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.heatmap(db, mode, sector)


@router.get("/technical/{symbol}", response_model=TechnicalResponse)
async def technical_indicators(
    symbol: str,
    timeframe: str = Query("1M", pattern="^(1D|1W|1M|1d|1w|1m)$"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await technical.technical(db, symbol, timeframe)


@router.get("/ai-insights", response_model=AIInsightResponse)
async def market_ai_insights(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    overview = await service.overview(db)
    sectors = await service.sectors(db)
    return {
        "scope": "market",
        "insights": ai_insights.market_insights(overview, sectors),
        "suggestion": None,
    }


@router.get("/ai-insights/{symbol}", response_model=AIInsightResponse)
async def symbol_ai_insights(
    symbol: str,
    timeframe: str = Query("1M", pattern="^(1D|1W|1M|1d|1w|1m)$"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    tech = await technical.technical(db, symbol, timeframe)
    return {
        "scope": symbol.upper(),
        "insights": tech["insights"],
        "suggestion": tech["suggestion"],
    }
