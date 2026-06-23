"use client";

import { useWatchlistStore } from "@/store/watchlist.store";

/** Convenience facade over the persisted watchlist store. */
export function useWatchlist() {
  const symbols = useWatchlistStore((s) => s.symbols);
  const add = useWatchlistStore((s) => s.add);
  const remove = useWatchlistStore((s) => s.remove);
  const toggle = useWatchlistStore((s) => s.toggle);

  return {
    symbols,
    count: symbols.length,
    add,
    remove,
    toggle,
    has: (symbol: string) => symbols.includes(symbol),
  };
}
