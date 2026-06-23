# Phase 10 — Mobile + Expansion

Turns the platform into a mobile-first, offline-capable, push-enabled ecosystem.

## Mobile-first web (PWA)

- **Bottom navigation** (`components/layout/BottomNav.tsx`) on small screens
  (`md:hidden`); the sidebar takes over on `md+`. Content gets `pb-20` on mobile
  so it clears the bar.
- **Installable PWA** — `public/manifest.json` + `public/icon.svg`, `theme-color`
  and `viewport` metadata, Apple web-app tags.
- **Offline-first** — a network-first **service worker** (`public/sw.js`,
  registered in `providers.tsx`) caches the app shell + GET responses; an
  `OfflineBanner` shows when connectivity drops (`useOnlineStatus`); the live
  market snapshot is mirrored to `localStorage` (`utils/offlineCache.ts`) for
  last-known-data rendering.
- **User-configurable alert preferences** — toggle UI on the Profile page
  (`components/mobile/NotificationSettings.tsx`) backed by `/mobile/preferences`.

## Backend mobile API (`/api/v1/mobile`)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/home` | **one round-trip**: overview + watchlist quotes + portfolio + prefs (battery-friendly) |
| GET/POST/DELETE | `/watchlist`, `/watchlist/{symbol}` | server-side watchlist (cross-device) |
| POST | `/watchlist/sync` | **offline-sync conflict resolution** |
| POST/GET/DELETE | `/devices` | FCM/APNs device-token registry |
| GET/PUT | `/preferences` | per-user notification channel/type prefs |

### Offline sync conflict resolution

Each watchlist item carries an epoch-ms `updated_at` and a `deleted` tombstone.
`/watchlist/sync` does **per-item last-write-wins**: for each symbol the side
with the greater `updated_at` wins (covers adds and deletes), server-only items
are preserved, and the full merged state (with tombstones) is returned so every
device converges. Add/remove also write tombstones so deletions propagate.

## Push notifications

`notifications/push.py` delivers via two paths from one `send_push(user_id, …)`:

1. **Web push** — Redis pub/sub on `notify:user:{id}` (WS bridge / service worker).
2. **Native push** — Firebase Cloud Messaging to the user's registered device
   tokens (legacy HTTP API, gated by `FCM_ENABLED`; logs when off).

Both are best-effort and isolated. The alert dispatch task now respects each
user's **notification preferences** (`channel_allowed`) before sending — a
disabled channel is logged as skipped, never delivered.

## React Native app (optional, not built here)

The mobile API is RN-ready: token auth (existing JWT + refresh), `/mobile/home`
for a single hydration call, `/watchlist/sync` for offline reconciliation,
`/mobile/devices` for FCM registration, and the live WebSocket feed. A native
build is intentionally out of scope for this repo (can't be verified here); the
backend contract is complete for an Expo/React Native client to consume.

## Config (`core/config.py`)

`FCM_ENABLED`, `FCM_SERVER_KEY`, `FCM_API_URL`, `MOBILE_SNAPSHOT_TTL`.

## Migration

`alembic upgrade head` applies `0003_mobile`: `watchlist_items`,
`device_tokens`, `notification_preferences`.

## Tests

- `tests/test_mobile.py` — watchlist add/list/remove, sync LWW (client-wins /
  server-wins), device dedupe/delete, preferences, aggregated home (7 cases).
- `tests/test_push.py` — FCM transport (disabled/enabled/mocked), channel
  preference gating, best-effort `send_push` (6 cases).

Backend: **116 tests pass.** Frontend: `tsc`, ESLint, and `next build` all clean.
