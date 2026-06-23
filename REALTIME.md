# Phase 3 — Real-Time Market System

End-to-end live market streaming for the NEPSE platform, built on the Phase 1
backend and Phase 2 frontend.

## Pipeline

```
NEPSE source / simulator
        │
        ▼
Celery ingestion worker  (fetch → clean/normalize → store)
        │  derive PriceUpdate + OHLCUpdate + change/%/volume
        ▼
Redis pub/sub  (BATCHED, one envelope per channel per tick, monotonic `seq`)
   market:prices   market:ohlc   market:volume
        │
        ▼
MarketBroadcaster  (one Redis subscriber per API process, auto-reconnect)
        │
        ▼
ConnectionManager  (connection pool + per-symbol/ticker subscription index)
        │  fan-out only to interested clients
        ▼
WebSocket  /ws/market   ──►   Next.js (useMarketSocket → Zustand → components)
```

## Backend (`backend/`)

| File | Role |
|------|------|
| `core/redis_client.py` | Channel constants (`market:prices/ohlc/volume`), seq key |
| `market_data/schemas.py` | `PriceUpdate`, `OHLCUpdate`, `build_updates()` (change/%/OHLC) |
| `celery_tasks/tasks.py` | `broadcast_updates` — batched multi-channel publish with `seq` |
| `websocket/manager.py` | `ConnectionManager`: connect/disconnect/subscribe/unsubscribe/route + heartbeat |
| `websocket/broadcaster.py` | `MarketBroadcaster`: Redis→WS routing, exponential-backoff reconnect |
| `websocket/routes.py` | `/ws/market` — JWT auth, subscribe/ticker/ping protocol |

**WebSocket protocol**

Client → server: `{"action":"subscribe","symbols":[...]}` ·
`{"action":"subscribe","channel":"ticker"}` ·
`{"action":"unsubscribe",...}` · `{"action":"ping"}`

Server → client: `{"type":"prices","seq":N,"data":[...]}` ·
`{"type":"ohlc",...}` · `{"type":"volume",...}` · `pong` · `heartbeat` · `connected`

**Payloads** match the spec exactly:
```json
{"symbol":"NABIL","price":542.5,"change":12.5,"change_percent":2.36,"volume":120034,"timestamp":"..."}
{"symbol":"NABIL","open":530,"high":550,"low":528,"close":542.5,"volume":120034,"interval":"1m","timestamp":"..."}
```

## Frontend (`frontend/`)

| File | Role |
|------|------|
| `hooks/useWebSocket.ts` | Single socket, ticker subscribe, ping, backoff reconnect |
| `store/market.store.ts` | `quotes` + `candles` maps, **seq-based dedup** |
| `components/market/MarketTicker.tsx` | Scrolling live ticker bar |
| `components/charts/CandlestickChart.tsx` | History `setData` + live `series.update()` (incremental) |
| `components/stocks/AnimatedPrice.tsx` | Green/red flash on every price change |
| `components/stocks/LivePrice.tsx` | Per-symbol live readout |

## Scaling & performance

- **Batched publishing**: one publish per channel per tick (all symbols) — no
  per-symbol flooding.
- **Targeted fan-out**: reverse index `symbol → {client}`; ticker clients share
  one JSON-encoded payload; per-symbol subscribers get only their slice.
- **Horizontal scale**: each API replica runs its own manager + Redis
  subscriber, so 10k+ connections spread across replicas all stay in sync via
  the shared Redis bus. Sub-500ms is the publish→client hop, independent of the
  ingestion tick interval (`MARKET_FETCH_INTERVAL`).
- **Minimal re-renders**: components select only their symbol's store slice;
  charts patch incrementally rather than re-rendering.

## Edge cases handled

| Case | Handling |
|------|----------|
| Disconnect / reconnect | Client exponential backoff; server heartbeat + dead-socket reaping |
| Keep-alive | App-level ping (client, 15s) + heartbeat (server, 20s) |
| Redis failure | Broadcaster reconnects with backoff; frontend falls back to REST `/market/live` polling |
| Duplicate / out-of-order | Monotonic `seq` per publish; store drops envelopes `seq ≤ lastSeq`; chart rejects bars older than the last |
| Malformed frames | Ignored on both ends |

## Operational additions

### Snapshot + replay (trading-grade state recovery)
- **Snapshot-on-subscribe**: the moment a client subscribes, the server pushes
  the current market snapshot (`{"type":"prices","snapshot":true,...}`) so new
  clients render live state instantly instead of waiting a tick.
- **Replay buffer**: each price envelope is appended to a capped Redis list
  (`market:replay`, last `REPLAY_MAX`). A client can request
  `{"action":"replay","from_seq":N}` to receive every envelope with `seq > N`
  in order (gap recovery / audit). Note: because each tick is a *full* snapshot,
  price state self-heals on the next tick — replay matters most for candle
  continuity and audit.

### Metrics (`/metrics`, `/metrics/prometheus`)
JSON + Prometheus exposition of: active/total WS connections, **messages/sec**,
dead-socket reaps, broadcaster envelopes, **Redis lag (ms)**, **sequence gaps
(dropped frames)**, reconnects, last seq.

### Load testing
`backend/scripts/loadtest_ws.py` opens N concurrent sockets, subscribes to the
ticker, and reports throughput + fan-out latency (p50/p95/p99):
```bash
python scripts/loadtest_ws.py -c 1000 -d 30     # 1k sockets, 30s
python scripts/loadtest_ws.py -c 5000 -d 30
python scripts/loadtest_ws.py -c 10000 -d 30
```
Watch `/metrics` during a run to correlate messages/sec and Redis lag.

### Full-stack Docker
Root `docker-compose.yml` builds Postgres + Redis + API + Celery worker + beat +
frontend (Next.js standalone image):
```bash
cp backend/.env.example backend/.env   # set SECRET_KEY
docker compose up --build              # frontend :3000, API :8000
```

## Notes

- The frontend subscribes to the `ticker` firehose (NEPSE's symbol set is
  bounded). The protocol fully supports per-symbol `subscribe`/`unsubscribe`
  for fine-grained scaling when the universe is large.
- Increase tick frequency by lowering `MARKET_FETCH_INTERVAL` in `backend/.env`.
