"""Test the Celery analytics precompute task end-to-end.

Drives ``refresh_analytics_snapshot`` with a fake Redis and a real synchronous
SQLite database (the path the worker uses), asserting it reads the live snapshot
and writes the dashboard payloads that the async API reads back.
"""
import json
from contextlib import contextmanager

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import celery_tasks.analytics_tasks as at
from core.database import Base
from core.redis_client import KEY_ANALYTICS, KEY_MARKET_SNAPSHOT
from stocks.models import Stock

TS = "2026-06-20T10:00:00+00:00"


class FakeRedis:
    def __init__(self):
        self.kv: dict = {}

    def get(self, key):
        return self.kv.get(key)

    def set(self, key, value, ex=None):
        self.kv[key] = value

    def pipeline(self):
        return self  # set() works the same; execute() is a no-op

    def execute(self):
        return None


def _snapshot():
    return [
        {"symbol": "NABIL", "price": 500, "change": 10, "change_percent": 2.0,
         "volume": 10_000, "timestamp": TS},
        {"symbol": "UPPER", "price": 300, "change": -9, "change_percent": -3.0,
         "volume": 20_000, "timestamp": TS},
    ]


@pytest.fixture
def env(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as s:
        s.add_all([
            Stock(symbol="NABIL", company_name="Nabil", sector="Bank"),
            Stock(symbol="UPPER", company_name="Upper", sector="Hydro"),
        ])
        s.commit()

    @contextmanager
    def fake_db():
        session = Session()
        try:
            yield session
            session.commit()
        finally:
            session.close()

    fake = FakeRedis()
    fake.kv[KEY_MARKET_SNAPSHOT] = json.dumps(_snapshot())
    monkeypatch.setattr(at, "get_sync_redis", lambda: fake)
    monkeypatch.setattr(at, "get_sync_db", fake_db)
    return fake


def test_refresh_writes_all_payloads(env):
    count = at.refresh_analytics_snapshot()
    assert count == 2

    overview = json.loads(env.kv[KEY_ANALYTICS.format(name="overview")])
    assert overview["total_stocks"] == 2
    assert overview["advancers"] == 1 and overview["decliners"] == 1

    sectors = json.loads(env.kv[KEY_ANALYTICS.format(name="sectors")])
    assert {s["sector"] for s in sectors} == {"Bank", "Hydro"}

    gainers = json.loads(env.kv[KEY_ANALYTICS.format(name="movers:gainers:10:0")])
    assert gainers[0]["symbol"] == "NABIL"

    heatmap = json.loads(env.kv[KEY_ANALYTICS.format(name="heatmap:change:all")])
    assert len(heatmap) == 2


def test_refresh_no_snapshot_is_noop(env):
    env.kv.pop(KEY_MARKET_SNAPSHOT)
    assert at.refresh_analytics_snapshot() == 0
