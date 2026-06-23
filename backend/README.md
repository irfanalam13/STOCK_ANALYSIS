# NEPSE Trading Backend

A production-grade, real-time stock market backend for NEPSE, built like a
"Bloomberg-lite" system: low-latency reads, a Celery-driven data pipeline, and
WebSocket broadcasts scaled via Redis pub/sub.

## Architecture

```
                       ┌──────────────┐
   Celery Beat ──────▶ │ run_market   │ every MARKET_FETCH_INTERVAL seconds
                       │ _pipeline    │
                       └──────┬───────┘
                              ▼   (chained Celery tasks)
   fetch_nepse_data ─▶ clean_market_data ─▶ store_market_data ─▶ broadcast_updates
        (source)          (validate)        (Postgres + Redis)     (Redis PUBLISH)
                                                                        │
                                              ┌─────────────────────────┘
                                              ▼
   Client ◀── WebSocket /ws/market ◀── ConnectionManager (Redis SUBSCRIBE per API replica)

   Client ── REST /api/v1/... ──▶ FastAPI ──▶ Redis cache (hit) | PostgreSQL (miss)
```

**Data flow:** Celery fetches → cleans/normalizes → stores in PostgreSQL +
caches in Redis → publishes to a Redis channel → every API process relays the
message to its local WebSocket clients.

## Layout

```
backend/
  core/          config, async+sync DB engines, Redis clients, security (JWT/bcrypt)
  auth/          register/login/refresh, JWT dependencies, RBAC
  users/         User model + management endpoints
  stocks/        stock catalog (Redis read-through cache) + history endpoint
  market_data/   models, fetcher (NEPSE source/simulator), processor, repository, routes
  websocket/     ConnectionManager (Redis pub/sub) + /ws/market endpoint
  celery_tasks/  worker (Celery app), tasks (4-stage pipeline), scheduler (beat)
  utils/         shared helpers + stock seeding
  tests/         unit (security, processor) + API (auth) + pipeline validation
```

## API

| Method | Path                              | Auth        | Purpose                       |
|--------|-----------------------------------|-------------|-------------------------------|
| POST   | `/api/v1/auth/register`           | public      | Create account                |
| POST   | `/api/v1/auth/login`              | public      | Get access + refresh tokens   |
| POST   | `/api/v1/auth/refresh`            | public      | Rotate tokens                 |
| GET    | `/api/v1/users/me`                | any user    | Current user                  |
| GET    | `/api/v1/users`                   | admin       | List users                    |
| GET    | `/api/v1/stocks`                  | any user    | List stocks (cached)          |
| POST   | `/api/v1/stocks`                  | admin       | Add a stock                   |
| GET    | `/api/v1/stocks/{symbol}`         | any user    | Stock detail                  |
| GET    | `/api/v1/stocks/{symbol}/history` | any user    | OHLCV history                 |
| GET    | `/api/v1/market/live`             | any user    | Live snapshot (Redis)         |
| GET    | `/api/v1/market/history`          | any user    | Historical market data        |
| WS     | `/ws/market?token=<access_jwt>`   | any user    | Real-time updates             |

## Run with Docker (recommended)

```bash
cd backend
cp .env.example .env          # then set a real SECRET_KEY
docker compose up --build
```

This starts PostgreSQL, Redis, the API (`:8000`), a Celery worker, and Celery
beat. Open http://localhost:8000/docs for interactive API docs.

## Run locally (without Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # set SECRET_KEY; ensure Postgres + Redis are reachable

# Terminal 1 — API (creates tables + seeds stocks on startup)
uvicorn main:app --reload

# Terminal 2 — Celery worker
celery -A celery_tasks.worker.celery_app worker --loglevel=info

# Terminal 3 — Celery beat (scheduler)
celery -A celery_tasks.worker.celery_app beat --loglevel=info
```

> On Windows, run the Celery worker with `--pool=solo`.

## Quick smoke test

```bash
# Register + login
curl -X POST localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"a@b.com","password":"pass1234","role":"trader"}'

TOKEN=$(curl -s -X POST localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"a@b.com","password":"pass1234"}' | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl localhost:8000/api/v1/market/live -H "Authorization: Bearer $TOKEN"
```

WebSocket (with `websocat`): `websocat "ws://localhost:8000/ws/market?token=$TOKEN"`

## Tests

```bash
cd backend
pip install -r requirements.txt
pytest            # uses in-memory SQLite; no Postgres/Redis needed
```

## NEPSE data source

NEPSE has no stable official public real-time API, so the fetcher ships with a
built-in market **simulator** (deterministic random walk over a seed catalog)
that makes the whole pipeline run with zero external dependencies. To use a
real upstream, set `NEPSE_API_URL` in `.env` and adapt
`market_data/fetcher.py::_parse_external_payload` to its JSON shape.

## Production notes

- Replace `Base.metadata.create_all` startup with **Alembic** migrations.
- Restrict CORS `allow_origins` to known frontends.
- Run multiple `api` replicas behind a load balancer — Redis pub/sub keeps
  WebSocket broadcasts consistent across them.
- Add a token blacklist table if you need refresh-token revocation.
```
