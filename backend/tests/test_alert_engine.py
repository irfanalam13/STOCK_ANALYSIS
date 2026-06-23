"""End-to-end simulation of the Celery evaluation engine.

Drives ``evaluate_alerts`` against a simulated market snapshot using a fake
Redis and a real synchronous SQLite database (the same path Celery workers
use). Notification dispatch is mocked, so this exercises the full match →
cooldown → rate-limit → log → enqueue flow without a broker or SMTP server.
"""
import json
from contextlib import contextmanager
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import alerts.cache as cache_mod
import celery_tasks.alert_tasks as at
from alerts.models import (
    AlertCondition,
    AlertType,
    NotificationChannel,
    NotificationStatus,
    NotificationLog,
    UserAlert,
)
from core.database import Base
from core.redis_client import (
    KEY_ALERT_SYMBOLS,
    KEY_MARKET_SNAPSHOT,
)
from market_data.models import MarketData
from stocks.models import Stock
from users.models import User

TS = "2026-06-20T10:00:00+00:00"


class FakeRedis:
    """Minimal in-process Redis stand-in for the engine's sync calls."""

    def __init__(self):
        self.kv: dict = {}
        self.sets: dict[str, set] = {}

    def get(self, key):
        return self.kv.get(key)

    def set(self, key, value, ex=None):
        self.kv[key] = str(value)

    def incr(self, key):
        self.kv[key] = str(int(self.kv.get(key, 0)) + 1)
        return int(self.kv[key])

    def expire(self, key, seconds):
        return True

    def exists(self, key):
        return 1 if key in self.kv else 0

    def delete(self, key):
        self.kv.pop(key, None)
        self.sets.pop(key, None)

    def smembers(self, key):
        return set(self.sets.get(key, set()))

    def sadd(self, key, *vals):
        self.sets.setdefault(key, set()).update(vals)


@pytest.fixture
def engine_env(monkeypatch):
    """Wire fake Redis + a seeded sync SQLite DB into the alert tasks."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    @contextmanager
    def fake_db():
        session = Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    fake = FakeRedis()
    monkeypatch.setattr(at, "get_sync_db", fake_db)
    monkeypatch.setattr(at, "get_sync_redis", lambda: fake)
    monkeypatch.setattr(cache_mod, "get_sync_redis", lambda: fake)

    captured: list[dict] = []
    monkeypatch.setattr(
        at.dispatch_notification, "apply_async",
        lambda args, queue=None: captured.append(args[0]),
    )

    return Session, fake, captured


def _seed(Session, *, alert_type, condition, threshold, volume_rows=None):
    with Session() as s:
        user = User(email="sim@x.com", hashed_password="x")
        stock = Stock(symbol="NABIL", company_name="Nabil Bank", sector="Bank")
        s.add_all([user, stock])
        s.flush()
        for v in (volume_rows or []):
            s.add(MarketData(stock_id=stock.id, open_price=500, high_price=500,
                             low_price=500, close_price=500, volume=v,
                             timestamp=datetime.now(timezone.utc)))
        s.add(UserAlert(user_id=user.id, stock_symbol="NABIL",
                        alert_type=alert_type, condition=condition,
                        threshold_value=threshold, channel=NotificationChannel.EMAIL,
                        cooldown_seconds=300))
        s.commit()
        return user.id


def _snapshot(fake, *, price, change_percent, volume):
    fake.kv[KEY_MARKET_SNAPSHOT] = json.dumps([
        {"symbol": "NABIL", "price": price, "change": 0.0,
         "change_percent": change_percent, "volume": volume, "timestamp": TS}
    ])
    fake.sets[KEY_ALERT_SYMBOLS] = {"NABIL"}


def test_price_spike_fires_and_enqueues(engine_env):
    Session, fake, captured = engine_env
    _seed(Session, alert_type=AlertType.PRICE,
          condition=AlertCondition.ABOVE, threshold=600)
    _snapshot(fake, price=620, change_percent=4.0, volume=10_000)

    fired = at.evaluate_alerts()

    assert fired == 1
    assert len(captured) == 1
    job = captured[0]
    assert job["channel"] == "email"
    assert job["payload"]["symbol"] == "NABIL"
    assert "above" in job["payload"]["reason"]

    with Session() as s:
        alert = s.query(UserAlert).one()
        assert alert.trigger_count == 1
        assert alert.last_triggered_at is not None
        log = s.query(NotificationLog).one()
        assert log.status == NotificationStatus.PENDING
    # Cooldown armed so the next tick won't re-fire.
    assert fake.exists(f"alerts:cooldown:{alert.id}")


def test_volume_spike_uses_average_baseline(engine_env):
    Session, fake, captured = engine_env
    # Avg of these rows = 1000; a 5000-volume tick is a 5× spike.
    _seed(Session, alert_type=AlertType.VOLUME, condition=AlertCondition.ABOVE,
          threshold=2, volume_rows=[1000, 1000, 1000, 1000])
    _snapshot(fake, price=500, change_percent=0.0, volume=5000)

    fired = at.evaluate_alerts()
    assert fired == 1
    assert "×" in captured[0]["payload"]["reason"]


def test_below_threshold_does_not_fire(engine_env):
    Session, fake, captured = engine_env
    _seed(Session, alert_type=AlertType.PRICE,
          condition=AlertCondition.ABOVE, threshold=700)
    _snapshot(fake, price=620, change_percent=4.0, volume=10_000)

    assert at.evaluate_alerts() == 0
    assert captured == []


def test_rate_limit_drops_notification(engine_env, monkeypatch):
    Session, fake, captured = engine_env
    monkeypatch.setattr(cache_mod.settings, "ALERT_RATE_LIMIT", 0)  # over budget
    _seed(Session, alert_type=AlertType.PRICE,
          condition=AlertCondition.ABOVE, threshold=600)
    _snapshot(fake, price=620, change_percent=4.0, volume=10_000)

    assert at.evaluate_alerts() == 0
    assert captured == []


def test_cooldown_suppresses_repeat(engine_env):
    Session, fake, captured = engine_env
    alert_id = None
    _seed(Session, alert_type=AlertType.PRICE,
          condition=AlertCondition.ABOVE, threshold=600)
    _snapshot(fake, price=620, change_percent=4.0, volume=10_000)

    assert at.evaluate_alerts() == 1      # first tick fires
    assert at.evaluate_alerts() == 0      # second tick is in cooldown
    assert len(captured) == 1


def test_empty_active_set_skips_evaluation(engine_env):
    Session, fake, captured = engine_env
    _seed(Session, alert_type=AlertType.PRICE,
          condition=AlertCondition.ABOVE, threshold=600)
    _snapshot(fake, price=620, change_percent=4.0, volume=10_000)
    # Simulate Redis index miss AND no DB rebuild target by deactivating.
    fake.sets[KEY_ALERT_SYMBOLS] = set()
    with Session() as s:
        s.query(UserAlert).update({UserAlert.is_active: False})
        s.commit()

    assert at.evaluate_alerts() == 0
