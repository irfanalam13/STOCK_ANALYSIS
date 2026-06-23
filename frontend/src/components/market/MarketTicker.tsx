"use client";

import Link from "next/link";
import { useMemo } from "react";

import { useMarketStore } from "@/store/market.store";
import type { LiveQuote } from "@/types";
import { ROUTES } from "@/utils/constants";
import { formatCurrency, formatPercent } from "@/utils/format";

function TickerItem({ q }: { q: LiveQuote }) {
  const up = q.change >= 0;
  return (
    <Link
      href={ROUTES.stock(q.symbol)}
      className="mx-4 inline-flex items-center gap-2 whitespace-nowrap text-sm hover:opacity-80"
    >
      <span className="font-semibold text-fg">{q.symbol}</span>
      <span className="tabular-nums text-fg">{formatCurrency(q.price)}</span>
      <span className={`tabular-nums ${up ? "text-up" : "text-down"}`}>
        {up ? "▲" : "▼"} {formatPercent(q.change_percent)}
      </span>
    </Link>
  );
}

/**
 * Horizontally scrolling live ticker. Reads the whole quote map from the
 * market store and renders the list twice so the marquee loops seamlessly.
 */
export function MarketTicker() {
  const quotes = useMarketStore((s) => s.quotes);
  const connected = useMarketStore((s) => s.connected);

  const items = useMemo(
    () => Object.values(quotes).sort((a, b) => a.symbol.localeCompare(b.symbol)),
    [quotes],
  );

  if (items.length === 0) return null;

  return (
    <div className="flex items-center border-b border-border bg-surface">
      <span
        className={`flex items-center gap-1.5 border-r border-border px-3 py-2 text-xs font-medium ${
          connected ? "text-up" : "text-muted"
        }`}
      >
        <span className={`h-2 w-2 rounded-full ${connected ? "bg-up animate-pulse" : "bg-muted"}`} />
        LIVE
      </span>
      <div className="group relative flex-1 overflow-hidden">
        <div className="ticker-track flex w-max py-2 group-hover:[animation-play-state:paused]">
          {[...items, ...items].map((q, i) => (
            <TickerItem key={`${q.symbol}-${i}`} q={q} />
          ))}
        </div>
      </div>
    </div>
  );
}
