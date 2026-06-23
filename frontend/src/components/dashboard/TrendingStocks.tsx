"use client";

import Link from "next/link";

import { Card, CardHeader } from "@/components/ui";
import { PriceChange } from "@/components/stocks/PriceChange";
import type { StockWithQuote } from "@/types";
import { ROUTES } from "@/utils/constants";
import { formatVolume } from "@/utils/format";

export function TrendingStocks({ rows }: { rows: StockWithQuote[] }) {
  return (
    <Card>
      <CardHeader title="Trending" subtitle="Most active by volume" />
      {rows.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted">No data yet.</p>
      ) : (
        <ul className="divide-y divide-border/60">
          {rows.map((s) => (
            <li key={s.id}>
              <Link
                href={ROUTES.stock(s.symbol)}
                className="flex items-center justify-between py-2.5 hover:opacity-80"
              >
                <div>
                  <span className="font-medium text-fg">{s.symbol}</span>
                  <span className="ml-2 text-xs text-muted">
                    Vol {formatVolume(s.volume)}
                  </span>
                </div>
                <PriceChange pct={s.changePct} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
