"""Stock catalog + per-symbol history endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user, require_roles
from core.database import get_db
from market_data import repository as md_repo
from market_data.schemas import MarketDataOut
from stocks import service
from stocks.schemas import StockCreate, StockOut
from users.models import User, UserRole

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("", response_model=list[StockOut])
async def list_stocks(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await service.list_stocks_cached(db)


@router.post("", response_model=StockOut, status_code=status.HTTP_201_CREATED)
async def create_stock(
    payload: StockCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    if await service.get_by_symbol(db, payload.symbol):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Symbol already exists"
        )
    return await service.create_stock(db, payload)


@router.get("/{symbol}", response_model=StockOut)
async def get_stock(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stock = await service.get_by_symbol(db, symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found"
        )
    return stock


@router.get("/{symbol}/history", response_model=list[MarketDataOut])
async def get_stock_history(
    symbol: str,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stock = await service.get_by_symbol(db, symbol)
    if not stock:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Stock not found"
        )
    return await md_repo.get_history_by_stock(db, stock.id, limit=limit)
