"""Pytest fixtures: in-memory SQLite app for fast, isolated API tests.

Tests do NOT require PostgreSQL or Redis — the DB dependency is overridden with
an aiosqlite engine and the app lifespan (which would touch Postgres/Redis) is
intentionally not triggered by the ASGI transport.
"""
import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Import models so they register on Base.metadata before create_all.
import alerts.models  # noqa: F401
import auth.models  # noqa: F401
import market_data.models  # noqa: F401
import mobile.models  # noqa: F401
import portfolio.models  # noqa: F401
import security.models  # noqa: F401
import stocks.models  # noqa: F401
import users.models  # noqa: F401
from core.database import Base, get_db
from main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestSession = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_get_db():
        async with TestSession() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    # Expose the session factory so tests can seed data on the same in-memory DB.
    # The audit middleware also uses it, so audit rows land in the test DB.
    app.state.test_session = TestSession
    # Don't throttle the broad suite; rate-limit tests opt in explicitly.
    app.state.rate_limit_enabled = False
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    await engine.dispose()
