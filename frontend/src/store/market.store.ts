import { create } from "zustand";

import type { Candle, LiveQuote } from "@/types";

interface MarketState {
  // symbol -> latest live quote, updated by the WebSocket hook.
  quotes: Record<string, LiveQuote>;
  // symbol -> latest OHLC candle, used for incremental chart patching.
  candles: Record<string, Candle>;
  connected: boolean;
  lastSeq: number;
  lastUpdate: string | null;

  setConnected: (connected: boolean) => void;
  /**
   * Merge a price batch. `seq` guards against duplicate / out-of-order
   * envelopes: anything not newer than the last applied sequence is dropped.
   * Pass seq=0 for the REST snapshot seed (always applied, never advances seq).
   */
  applyPrices: (seq: number, updates: LiveQuote[]) => void;
  applyCandles: (seq: number, updates: Candle[]) => void;
}

export const useMarketStore = create<MarketState>((set, get) => ({
  quotes: {},
  candles: {},
  connected: false,
  lastSeq: 0,
  lastUpdate: null,

  setConnected: (connected) => set({ connected }),

  applyPrices: (seq, updates) => {
    // Duplicate / out-of-order envelope filtering.
    if (seq > 0 && seq <= get().lastSeq) return;
    if (updates.length === 0) return;
    set((state) => {
      const quotes = { ...state.quotes };
      for (const q of updates) quotes[q.symbol] = q;
      return {
        quotes,
        lastSeq: seq > 0 ? seq : state.lastSeq,
        lastUpdate: updates[0]?.timestamp ?? state.lastUpdate,
      };
    });
  },

  applyCandles: (seq, updates) => {
    if (updates.length === 0) return;
    set((state) => {
      const candles = { ...state.candles };
      for (const c of updates) candles[c.symbol] = c;
      return { candles };
    });
  },
}));
