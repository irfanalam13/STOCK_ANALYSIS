# NEPSE AI — Trading Dashboard (Phase 2 Frontend)

Production-grade Next.js (App Router) trading dashboard for the NEPSE platform,
wired to the Phase 1 FastAPI backend. Modern fintech UI, dark/light themes,
real-time WebSocket price updates, and a clean, API-ready architecture.

## Tech stack

- **Next.js 14** (App Router) + **TypeScript**
- **Tailwind CSS** with semantic CSS-variable theme tokens (dark + light)
- **TanStack Query** for server-state caching/syncing
- **Zustand** for client state (auth, watchlist, live market)
- **Axios** service layer with JWT injection + transparent refresh-on-401
- **TradingView Lightweight Charts** (candles, line/area, volume)

## Getting started

```bash
cd frontend
cp .env.local.example .env.local      # points at http://localhost:8000
npm install
npm run dev                           # http://localhost:3000
```

Make sure the Phase 1 backend is running (`backend/` → `docker compose up`) so
auth, stock, and live-market endpoints respond. Register a user from the
`/auth/signup` page, then explore the dashboard.

## Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | Dev server |
| `npm run build` | Production build |
| `npm run start` | Serve the production build |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | Next/ESLint |

## Architecture

```
src/
  app/
    auth/{login,signup}/         public auth pages
    (protected)/                 route group — auth-gated app shell
      dashboard/                 market overview, index, gainers/losers, trending
      stocks/                    sortable + paginated + searchable table
      stocks/[symbol]/           detail: live price, candle/line/volume charts
      watchlist/                 managed watchlist table
      profile/                   account details
    providers.tsx                QueryClient + Theme + session bootstrap
  components/
    ui/                          Button, Card, Table, Modal, Loader, Input, Dropdown, Badge
    layout/                      Sidebar, Topbar, ProtectedShell, theme
    charts/                      ChartContainer + Candlestick/Line/Volume
    dashboard/ stocks/ watchlist/  feature components
  hooks/        useAuth, useStocks, useWatchlist, useWebSocket
  services/api/ axios (interceptors), auth/stocks/market endpoints, tokenStore
  store/        auth.store, watchlist.store, market.store
  utils/        format, constants, helpers, types
```

## Data flow

- **REST** via `services/api`, cached by **TanStack Query** hooks (`useStocks`,
  `useLiveSnapshot`, `useStockHistory`).
- **Live updates**: `ProtectedShell` opens one WebSocket (`useMarketSocket`) to
  `/ws/market?token=…`; every broadcast lands in `market.store`, and components
  like `LivePrice` subscribe to just their symbol's slice (minimal re-renders).
- **Stock catalog + live quotes** are joined in `useStocksWithQuotes` →
  `StockWithQuote[]`, which powers the tables, cards, and movers lists.

## Auth & security (UI level)

- JWT access/refresh stored via `tokenStore`; Axios attaches the bearer token.
- On `401`, a single shared refresh attempt replays the request; failure clears
  tokens and triggers **auto-logout** (`setAuthFailureHandler`).
- `(protected)` layout gates every app route and redirects to `/auth/login`.

## Performance

- Route-level code splitting (App Router) + memoized derived data (`useMemo`).
- Per-symbol store selectors avoid global re-renders on each tick.
- Chart lifecycle (create/resize/destroy) isolated in `ChartContainer` with a
  `ResizeObserver` for responsiveness.

## Notes / next steps

- Watchlist persists to `localStorage` (per spec); swap the Zustand `persist`
  storage for an API-backed store later without touching components.
- Token storage uses `localStorage` for the MVP — move to httpOnly cookies for
  hardened production security.
- The "NEPSE index" on the dashboard is a synthetic volume-weighted average
  derived from live quotes (the backend exposes per-stock data, not an index).
```
