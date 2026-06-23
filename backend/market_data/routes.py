"""Market data endpoints: live snapshot (cache-first) and history."""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from core.database import get_db
from core.redis_client import KEY_MARKET_SNAPSHOT, get_redis
from market_data import repository as repo
from market_data.schemas import MarketDataOut
from users.models import User

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/live")
async def live_market(_: User = Depends(get_current_user)) -> dict:
    """Return the latest market snapshot straight from Redis (low latency).

    The snapshot is written by the Celery broadcast task, so reads never touch
    PostgreSQL.
    """
    cached = await get_redis().get(KEY_MARKET_SNAPSHOT)
    if not cached:
        return {"quotes": [], "source": "cache", "stale": True}
    return {"quotes": json.loads(cached), "source": "cache", "stale": False}


@router.get("/history", response_model=list[MarketDataOut])
async def market_history(
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await repo.get_history_range(db, start=start, end=end, limit=limit)
