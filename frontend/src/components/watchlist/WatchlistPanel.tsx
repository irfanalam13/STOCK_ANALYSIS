"use client";

import Link from "next/link";

import { Card, CardHeader } from "@/components/ui";
import { PriceChange } from "@/components/stocks/PriceChange";
import { useStocksWithQuotes } from "@/hooks/useStocks";
import { useWatchlist } from "@/hooks/useWatchlist";
import { ROUTES } from "@/utils/constants";
import { formatCurrency } from "@/utils/format";

/** Compact watchlist used both on the dashboard and as a side panel. */
export function WatchlistPanel({ limit }: { limit?: number }) {
  const { symbols } = useWatchlist();
  const { data } = useStocksWithQuotes();

  const rows = data
    .filter((s) => symbols.includes(s.symbol))
    .slice(0, limit ?? symbols.length);

  return (
    <Card>
      <CardHeader
        title="Watchlist"
        subtitle={`${symbols.length} symbol${symbols.length === 1 ? "" : "s"}`}
        action={
          <Link href={ROUTES.watchlist} className="text-xs text-brand hover:underline">
            View all
          </Link>
        }
      />
      {rows.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted">
          No stocks yet. Add some from any stock page.
        </p>
      ) : (
        <ul className="divide-y divide-border/60">
          {rows.map((s) => (
            <li key={s.id}>
              <Link
                href={ROUTES.stock(s.symbol)}
                className="flex items-center justify-between py-2.5 hover:opacity-80"
              >
                <span className="font-medium text-fg">{s.symbol}</span>
                <span className="flex items-center gap-3">
                  <span className="tabular-nums text-fg">
                    {formatCurrency(s.price)}
                  </span>
                  <PriceChange pct={s.changePct} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
