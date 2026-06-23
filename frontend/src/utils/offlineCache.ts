// Offline-first cache layer (localStorage). Stores JSON snapshots with a
// timestamp so the UI can render last-known data while offline and show how
// stale it is. Swap the backing store for IndexedDB if payloads grow large.

const PREFIX = "nepse.cache.";

interface CacheEntry<T> {
  data: T;
  cachedAt: number; // epoch ms
}

export function cacheSet<T>(key: string, data: T): void {
  if (typeof window === "undefined") return;
  try {
    const entry: CacheEntry<T> = { data, cachedAt: Date.now() };
    localStorage.setItem(PREFIX + key, JSON.stringify(entry));
  } catch {
    // Quota exceeded / private mode — caching is best-effort.
  }
}

export function cacheGet<T>(key: string): { data: T; cachedAt: number } | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(PREFIX + key);
    if (!raw) return null;
    return JSON.parse(raw) as CacheEntry<T>;
  } catch {
    return null;
  }
}

export const CACHE_KEYS = {
  snapshot: "market.snapshot",
  watchlist: "watchlist",
  portfolio: "portfolio.summary",
} as const;
