"use client";

import { useMarketStore } from "@/store/market.store";
import { formatCurrency } from "@/utils/format";
import { AnimatedPrice } from "./AnimatedPrice";
import { PriceChange } from "./PriceChange";

/**
 * Live price readout. Subscribes to this single symbol's slice of the market
 * store, so it re-renders only when that symbol updates (via WebSocket).
 */
export function LivePrice({ symbol }: { symbol: string }) {
  const quote = useMarketStore((s) => s.quotes[symbol]);
  const connected = useMarketStore((s) => s.connected);

  return (
    <div className="flex items-end gap-3">
      <AnimatedPrice
        value={quote?.price ?? null}
        format={formatCurrency}
        className="text-3xl font-bold"
      />
      <PriceChange pct={quote?.change_percent ?? null} />
      <span
        className="mb-1 flex items-center gap-1.5 text-xs text-muted"
        title={connected ? "Live" : "Reconnecting…"}
      >
        <span
          className={`h-2 w-2 rounded-full ${connected ? "bg-up animate-pulse" : "bg-muted"}`}
        />
        {connected ? "Live" : "Offline"}
      </span>
    </div>
  );
}
