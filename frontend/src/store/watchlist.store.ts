import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

import { STORAGE_KEYS } from "@/utils/constants";

interface WatchlistState {
  symbols: string[];
  add: (symbol: string) => void;
  remove: (symbol: string) => void;
  toggle: (symbol: string) => void;
  has: (symbol: string) => boolean;
}

// Persisted to localStorage per the spec ("persistent storage, localStorage
// initially"). Swap the storage for an API-backed one later without touching
// component code.
export const useWatchlistStore = create<WatchlistState>()(
  persist(
    (set, get) => ({
      symbols: [],
      add: (symbol) =>
        set((s) =>
          s.symbols.includes(symbol)
            ? s
            : { symbols: [...s.symbols, symbol] },
        ),
      remove: (symbol) =>
        set((s) => ({ symbols: s.symbols.filter((x) => x !== symbol) })),
      toggle: (symbol) =>
        get().has(symbol) ? get().remove(symbol) : get().add(symbol),
      has: (symbol) => get().symbols.includes(symbol),
    }),
    {
      name: STORAGE_KEYS.watchlist,
      storage: createJSONStorage(() => localStorage),
    },
  ),
);
