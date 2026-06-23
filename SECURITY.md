# Phase 8 — Security & Scalability Hardening

Production-grade protections and scale wiring for the NEPSE AI platform.

## Middleware stack

Request order (outermost → innermost), set in `main.py`:

```
CORS → SecurityHeaders → RateLimit → Audit → routes
```

- **CORS** — origins from `CORS_ORIGINS` (strict in prod; `credentials` auto-off when `*`).
- **SecurityHeaders** (`security/headers.py`) — `X-Content-Type-Options`,
  `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, COOP, and
  opt-in HSTS (`HSTS_ENABLED`, only behind HTTPS). Applies to every response,
  including rate-limit 429s.
- **RateLimit** (`security/ratelimit.py`) — Redis fixed-window counter,
  per-user when a JWT is present else per-IP, **tier-based** limits. Emits
  `X-RateLimit-*` headers and `Retry-After`. **Fails open** if Redis is down.
- **Audit** (`security/audit.py`) — auto-logs every mutating `/api` request.

## Rate-limit tiers (per minute)

| Tier | Role | Limit |
|------|------|-------|
| Anonymous | (per-IP) | `RATE_LIMIT_ANON` = 30 |
| Free | viewer | `RATE_LIMIT_FREE` = 100 |
| Premium | trader / analyst | `RATE_LIMIT_PREMIUM` = 1000 |
| Admin | admin | `RATE_LIMIT_ADMIN` = 5000 |

## RBAC (`security/rbac.py`)

Roles: **Admin · Analyst · Trader · Free (viewer)**. A permission matrix maps
each role to fine-grained permissions (`market:read`, `analytics:read`,
`portfolio:read`, `portfolio:trade`, `alerts:write`, `admin:audit`,
`admin:users`, `admin:fraud`); ADMIN holds `*`. Enforce with the
`require_permission("…")` dependency. `GET /api/v1/security/me/permissions`
returns the caller's effective permissions and rate tier.

## Audit logs

`AuditLog` (PostgreSQL, indexed on `(user_id, timestamp)` and `(action, timestamp)`)
records user_id, action, method, path, status, IP, user-agent, metadata, and
timestamp. The middleware logs all POST/PUT/PATCH/DELETE under `/api`
(trades, alert changes, auth, profile…). Admin: `GET /api/v1/security/audit`.
`record_audit()` is reusable for explicit critical-action logging.

## Encryption vs hashing (`security/encryption.py`)

- **Passwords → hashed** (bcrypt, irreversible) — `core/security.py`.
- **Sensitive recoverable data → encrypted** (AES/Fernet, reversible) —
  `encrypt`/`decrypt`/`mask`. Key from `DATA_ENCRYPTION_KEY`, else derived from
  `SECRET_KEY`.

## API keys (`security/apikey.py`)

`require_api_key` validates the `X-API-Key` header against `API_KEYS` for
external/service-to-service callers.

## WebSocket hardening (`websocket/routes.py`)

1. JWT-authenticated handshake (token query param) before `accept`.
2. Per-socket sliding-window **message rate limit** (`WS_MSG_RATE_LIMIT` /
   `WS_MSG_WINDOW`) — abusive sockets are closed (`security/ws_guard.py`).
3. **Idle auto-disconnect** after `WS_IDLE_TIMEOUT` seconds.

## Fraud detection (`security/fraud.py`)

Rule-based, explainable, runs off the request path on the low-priority Celery
queue every 5 minutes (also on-demand via `POST /api/v1/security/fraud/scan`):

- **rapid_trading** — > `FRAUD_MAX_TRADES` trades in `FRAUD_TRADE_WINDOW`.
- **request_spike** — > `FRAUD_MAX_REQUESTS` API calls in `FRAUD_REQUEST_WINDOW`.

Raises `AccountFlag` rows (deduped while unresolved) for admin review:
`GET /api/v1/security/fraud/flags`, `PATCH …/{id}/resolve`.

## Scalability

- **Stateless API** → horizontal scale behind Nginx (`deploy/nginx.conf`):
  TLS termination, `least_conn` load balancing across replicas, WebSocket
  upgrade proxy, edge rate limiting. Run multiple Uvicorn/Gunicorn workers.
- **Celery priority queues** — high-priority (`alert-evaluation-queue`,
  `notification-send-queue`, `email-delivery-queue`) on `alerts-worker`;
  low-priority (`low-priority`: analytics refresh, fraud scan, logs) on the
  default `worker`. Tasks use `acks_late` + retry. Scale with
  `docker compose up --scale alerts-worker=N`.
- **Caching** — Redis for live quotes, market snapshot, analytics payloads,
  rate-limit counters, and indicator caches (best-effort, fail-open).
- **DB** — indexes on `user_id`, `stock_symbol`, and timestamps across
  `market_data`, `user_alerts`, `notification_logs`, `audit_logs`,
  `account_flags`; partition large historical tables and add read replicas for
  analytics queries in production.

## Migration

`alembic upgrade head` applies `0002_security_audit_fraud`: creates
`audit_logs` + `account_flags` and adds the `analyst` enum value.

## Tests

- `tests/test_security_hardening.py` — encryption, RBAC matrix, rate-limit
  counter, WS limiter, API key (10 cases).
- `tests/test_security_api.py` — security headers, permission tiers, admin RBAC
  (403/200), audit middleware end-to-end, fraud scan + resolve, rate-limit 429
  (6 cases).

Backend: **104 tests pass.**
