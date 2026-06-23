"use client";

import Link from "next/link";

import { Card, CardHeader } from "@/components/ui";
import { PriceChange } from "@/components/stocks/PriceChange";
import type { StockWithQuote } from "@/types";
import { ROUTES } from "@/utils/constants";
import { formatCurrency } from "@/utils/format";

function MoverList({ rows }: { rows: StockWithQuote[] }) {
  if (rows.length === 0)
    return <p className="py-6 text-center text-sm text-muted">No data yet.</p>;
  return (
    <ul className="divide-y divide-border/60">
      {rows.map((s) => (
        <li key={s.id}>
          <Link
            href={ROUTES.stock(s.symbol)}
            className="flex items-center justify-between py-2.5 hover:opacity-80"
          >
            <span className="font-medium text-fg">{s.symbol}</span>
            <span className="flex items-center gap-3">
              <span className="tabular-nums text-fg">{formatCurrency(s.price)}</span>
              <PriceChange pct={s.changePct} />
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function GainersLosers({
  gainers,
  losers,
}: {
  gainers: StockWithQuote[];
  losers: StockWithQuote[];
}) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <Card>
        <CardHeader title="Top Gainers" />
        <MoverList rows={gainers} />
      </Card>
      <Card>
        <CardHeader title="Top Losers" />
        <MoverList rows={losers} />
      </Card>
    </div>
  );
}
