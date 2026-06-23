"""Shared helpers used across modules."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from market_data.fetcher import NEPSE_SEED_STOCKS
from stocks.models import Stock


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def seed_stocks(db: AsyncSession) -> int:
    """Insert the seed NEPSE catalog if the stocks table is empty.

    Idempotent: only inserts symbols that don't already exist.
    """
    existing = set(
        (await db.execute(select(Stock.symbol))).scalars().all()
    )
    created = 0
    for item in NEPSE_SEED_STOCKS:
        if item["symbol"] in existing:
            continue
        db.add(Stock(**item))
        created += 1
    if created:
        await db.commit()
    return created
