"""Database engines and session factories.

Two engines are intentionally maintained:

* ``async_engine`` / ``AsyncSessionLocal`` — used by the FastAPI request path
  for non-blocking, low-latency reads and writes.
* ``sync_engine`` / ``SyncSessionLocal`` — used by Celery tasks, which run in a
  classic synchronous worker process.

Both share the same declarative ``Base`` so models are defined once.
"""
from collections.abc import AsyncGenerator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model in the project."""


# ---- Async (FastAPI) ----
# asyncpg does not read libpq's ``sslmode`` from the URL, so when a hosted
# DATABASE_URL requires SSL (Neon/Supabase/Render), enable it via connect_args.
_async_connect_args = {"ssl": True} if settings.DB_SSL_REQUIRED else {}
async_engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    connect_args=_async_connect_args,
)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, expire_on_commit=False, class_=AsyncSession
)

# ---- Sync (Celery) ----
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC, pool_pre_ping=True, pool_size=10, max_overflow=5
)
SyncSessionLocal = sessionmaker(bind=sync_engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async session with commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@contextmanager
def get_sync_db():
    """Context manager for Celery tasks needing a synchronous session."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def init_models() -> None:
    """Create tables on startup (dev convenience; use Alembic in production)."""
    # Import models so they register on Base.metadata before create_all.
    import alerts.models  # noqa: F401
    import auth.models  # noqa: F401
    import market_data.models  # noqa: F401
    import mobile.models  # noqa: F401
    import portfolio.models  # noqa: F401
    import security.models  # noqa: F401
    import stocks.models  # noqa: F401
    import users.models  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
