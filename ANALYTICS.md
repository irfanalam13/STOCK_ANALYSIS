# Phase 7 — Advanced Analytics Dashboard

A Bloomberg-/TradingView-style analytics layer over the live NEPSE feed: market
overview, sector strength, gainers/losers, heatmaps, a technical-indicator
engine, and a rule-based AI insights panel.

## Data flow

```
Market pipeline (Phase 3): fetch → clean → store → broadcast → (alerts) → analytics
        │  broadcast caches the enriched snapshot at market:snapshot
        ▼
refresh_analytics_snapshot   (Celery, appended to the pipeline chain)
   • precompute overview / sectors / movers / heatmaps from the snapshot
   • write to analytics:* Redis keys (warm cache, ~3 ticks TTL)
        ▼
FastAPI /analytics/*   (read-through: cache hit → <1s; miss → compute + cache)
        ▼
Next.js dashboard      (React Query, 15s safety-net poll; live prices via WS)
```

The number-crunching lives in **pure, I/O-free modules** reused by both paths:

- `analytics/indicators.py` — SMA, EMA, RSI (Wilder), MACD, Bollinger Bands,
  plus `compute_all` (latest values + buy/sell signals).
- `analytics/aggregator.py` — overview, sectors, movers, heatmap from snapshot rows.
- `analytics/ai_insights.py` — natural-language interpretation + probabilistic
  Buy/Sell/Hold suggestion.

> **Market cap note:** NEPSE listed-share counts aren't in our dataset, so a true
> market cap can't be computed. We use **turnover** (price × volume) as the size
> proxy and a turnover-weighted index level.

## API (`/api/v1/analytics`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/overview` | index proxy, breadth, volume/turnover, sentiment |
| GET | `/sectors` | per-sector performance + relative strength |
| GET | `/gainers` · `/losers` | top movers (`top`, `min_volume` — liquidity-aware) |
| GET | `/heatmap` | tiles grouped by sector (`mode=change\|volume`, `sector=`) |
| GET | `/technical/{symbol}` | indicator series + latest + signals (`timeframe=1D\|1W\|1M`) |
| GET | `/ai-insights` | market-wide narrative |
| GET | `/ai-insights/{symbol}` | per-symbol insights + suggestion |

All routes require auth. Redis access is **best-effort** — if the cache is down,
aggregations compute directly and the dashboard degrades gracefully.

## Technical indicators

Pure series math returning values aligned to the input (`None` during warm-up).
Signals follow standard conventions: RSI > 70 overbought / < 30 oversold; MACD
histogram sign = trend; price vs SMA50 = trend confirmation. Timeframes map to
recent OHLCV row counts (1D→60, 1W→200, 1M→500); a symbol needs
`ANALYTICS_MIN_HISTORY` (35) rows or the endpoint returns 422.

## AI insights

Deterministic, dependency-free, <1ms — meeting the <500ms target without a heavy
model, with a clean seam to swap in an ML classifier later. Produces lines like
*"Market is showing bullish momentum, led by Commercial Bank (+1.80%)"* and
*"MACD crossover suggests a potential upward trend in NABIL."* The suggestion is
a confidence-scored blend of RSI/MACD/SMA — **probabilistic, not advice**.

## Frontend (Next.js)

Sidebar **Analytics** section → six pages under `/dashboard`:

| Route | Content |
|-------|---------|
| `/dashboard/overview` | index hero + sentiment gauge, stat cards, movers, sectors, AI |
| `/dashboard/sectors` | sector table with diverging performance bars + relative strength |
| `/dashboard/gainers-losers` | dual tables with volume filters + top-N controls |
| `/dashboard/heatmap` | color-coded tiles grouped by sector; equal / volume-weighted; click-to-drill |
| `/dashboard/technical` | lightweight-charts price + SMA/EMA/Bollinger overlays, indicator readouts, signals, suggestion |
| `/dashboard/ai-insights` | market narrative + per-stock insights & suggestion |

Built on the existing UI kit (`Card`, `Badge`, `ConfidenceMeter`, `ChartContainer`)
and `lightweight-charts`. Service: `services/api/analytics.api.ts`; hooks:
`hooks/useAnalytics.ts` (React Query, dark-mode trading-terminal styling).

## Performance

- **<1s loads** — pipeline precomputes payloads into Redis each tick; API reads
  are cache hits. Read-through fallback caches on miss (`ANALYTICS_CACHE_TTL` 8s;
  indicators `ANALYTICS_INDICATOR_TTL` 60s).
- **Live freshness** — recompute runs in lock-step with the market tick; the
  frontend also polls every 15s as a socket-drop safety net.

## Tests

- `tests/test_indicators.py` — indicator math invariants (10 cases).
- `tests/test_aggregator.py` — aggregations + AI insight/suggestion logic (11 cases).
- `tests/test_analytics_api.py` — API: auth, empty-state, technical, errors (8 cases).
- `tests/test_analytics_engine.py` — Celery precompute task end-to-end (2 cases).

Backend: **88 tests pass**. Frontend: `tsc`, ESLint, and `next build` all clean
(6 new pages prerender).
