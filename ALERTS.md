# Phase 6 — Alerts & Notifications System

A real-time, event-driven alert engine layered on the Phase 3 market pipeline.
Users register conditions against live market data; a Celery stage evaluates
them on every tick and fans matches out through a multi-channel notification
layer (email now; SMS and push are pluggable).

## Event flow

```
Market pipeline (Phase 3): fetch → clean → store → broadcast_updates
        │  broadcast_updates caches the enriched snapshot at market:snapshot
        ▼
evaluate_alerts            [queue: alert-evaluation-queue]
   • read market:snapshot (price, change%, volume per symbol)
   • intersect with alerts:active-symbols (Redis set)  → skip DB if empty
   • load active alerts for watched symbols (indexed, no full scan)
   • match via pure evaluator + per-alert cooldown + per-user rate limit
   • write pending NotificationLog rows, enqueue one dispatch job each
        ▼
dispatch_notification      [queue: notification-send-queue]
   • resolve recipient, route by channel
   • email → hand to delivery queue; sms/push → send inline, finalize log
        ▼
deliver_email              [queue: email-delivery-queue]
   • SMTP send with Celery auto-retry + exponential backoff
   • finalize NotificationLog (sent / failed)
```

`evaluate_alerts` is appended to the market-pipeline `chain`, so alerting is
**event-driven per tick** — no separate polling loop. It ignores its chained
input and reads the cached snapshot, keeping it decoupled from the pipeline's
payload shape.

## Alert types

| Type      | Threshold means          | Conditions          | Notes                                   |
|-----------|--------------------------|---------------------|-----------------------------------------|
| `price`   | absolute price (NPR)     | above / below / equal | `equal` needs a `tolerance` band       |
| `percent` | intraday change (%)      | above / below / equal | compares `change_percent`              |
| `volume`  | multiplier (e.g. 2×, 5×) | above               | vs. cached avg volume (`VOLUME_AVG_LOOKBACK`) |

Trigger logic lives in `alerts/evaluator.py` as a pure, I/O-free function so it
is exhaustively unit-testable and cheap to batch.

## Scaling & performance

- **No full DB scans.** `alerts:active-symbols` (Redis set) gates every tick; a
  tick with no watched symbols never touches Postgres. When symbols *are*
  watched, the query rides `ix_user_alerts_active_symbol (is_active, stock_symbol)`.
- **Queue isolation.** Evaluation, dispatch, and email delivery each have their
  own queue, so slow SMTP I/O never blocks condition matching. Scale each tier
  independently: `docker compose up --scale alerts-worker=N`, or pin workers to
  queues with `-Q`.
- **Avg-volume caching.** Per-symbol baselines are cached in Redis
  (`alerts:volavg:{symbol}`, TTL `VOLUME_AVG_CACHE_TTL`).
- **Cold-cache rebuild.** If Redis is flushed, `evaluate_alerts` rebuilds the
  active-symbol index from the DB once, then resumes the fast path.

## Anti-spam & security

- **Per-alert cooldown** (`cooldown_seconds`) silences an alert after it fires —
  a price hovering at a threshold can't flood the user.
- **Per-user rate limit** (`ALERT_RATE_LIMIT` per `ALERT_RATE_WINDOW`) is the
  platform-wide flood guard; over-budget triggers are dropped and logged.
- **Per-user alert quota** (`ALERT_MAX_PER_USER`).
- **Server-side validation** — thresholds must be positive; `equal` requires a
  tolerance; `volume` only allows `above`; the symbol must exist in the catalog.
- **Ownership scoping** — every alert route requires auth and is filtered to the
  caller; cross-user access returns 404.

## Data models (`alerts/models.py`)

- **`UserAlert`** — `user_id`, `stock_symbol`, `alert_type`, `condition`,
  `threshold_value`, `tolerance`, `channel`, `cooldown_seconds`, `is_active`,
  `trigger_count`, `last_triggered_at`.
- **`NotificationLog`** — immutable audit row per delivery attempt: `user_id`,
  `alert_id`, `channel`, `subject`, `message`, `status`, `error`, `attempts`.

## Notification layer (`notifications/`)

`NotificationService` is the single seam the engine talks to:

```python
service.send_email(recipient, payload)   # multipart HTML + text (SMTP)
service.send_sms(recipient, payload)     # Twilio-ready (lazy import)
service.send_push(recipient, payload)    # publishes to notify:user:{id}; FCM/APNs-ready
service.dispatch(channel, recipient, payload)
```

Adding a channel = one transport module + one method; nothing upstream changes.
Email bodies are rendered from `notifications/templates.py` (self-contained HTML
with a mandatory plain-text fallback).

**Email → SMS fallback.** When `deliver_email` exhausts its retries, it falls
back to SMS for users who have a phone number on file (`SMS_ENABLED=true`),
recording a separate `NotificationLog` row. A failed email never cascades into a
task error.

**Daily digest.** `send_daily_digest` (Celery Beat, 16:30 UTC after NEPSE close)
emails each user one consolidated summary of their active alerts and trigger
counts — an opt-out of per-tick noise.

## User contact for SMS

`User.phone` is nullable and set via `PATCH /api/v1/users/me` (`{"phone": ...}`);
`GET /api/v1/users/me` returns it. It is not collected at registration. SMS
delivery stays log-and-fail-soft until a number is present and `SMS_ENABLED`.

## API (`/api/v1/alerts`)

| Method | Path                            | Purpose                       |
|--------|---------------------------------|-------------------------------|
| POST   | `/alerts`                       | create an alert               |
| GET    | `/alerts`                       | list my alerts                |
| GET    | `/alerts/{id}`                  | get one (owner-scoped)        |
| PATCH  | `/alerts/{id}`                  | update / activate / deactivate|
| DELETE | `/alerts/{id}`                  | delete                        |
| GET    | `/alerts/notifications/history` | my notification log           |

## Configuration (`core/config.py`)

Alert tunables (`ALERT_*`, `VOLUME_AVG_*`) and delivery settings
(`EMAIL_*`/`SMTP_*`, `SMS_*`/`TWILIO_*`). `EMAIL_ENABLED=false` (default) logs
instead of sending, so the full pipeline is exercisable without a real SMTP
server; `SMS_ENABLED=false` behaves likewise.

## Running

```bash
# All services (api, market worker, alerts worker, beat, redis, postgres):
docker compose up --build

# Scale the alert tier:
docker compose up --scale alerts-worker=3

# Locally, a worker that handles every alert queue:
celery -A celery_tasks.worker.celery_app worker \
  -Q alert-evaluation-queue,notification-send-queue,email-delivery-queue
```

## Tests

- `tests/test_alert_evaluator.py` — pure trigger logic (price/percent/volume).
- `tests/test_notifications.py` — templates + channel routing (mocked transport).
- `tests/test_alerts_api.py` — CRUD, validation, ownership isolation.
- `tests/test_alert_engine.py` — end-to-end `evaluate_alerts` market-spike
  simulation (fake Redis + sync SQLite): firing, volume baseline, cooldown,
  rate-limit drop, empty-set skip.
- `tests/test_user_profile.py` — phone update endpoint.

## Load testing

`scripts/loadtest_alerts.py` benchmarks the evaluation hot path:

```bash
python scripts/loadtest_alerts.py --alerts 1000000 --symbols 300 --ticks 20
```

Reports per-tick latency percentiles and throughput against the <500ms target.
Measured ~600k alerts/s single-threaded — the matching core sustains well above
the "thousands per second" requirement; broker/SMTP I/O scales separately via
additional `alerts-worker` replicas.
