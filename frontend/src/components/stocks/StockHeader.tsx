"use client";

import { Badge } from "@/components/ui";
import { WatchlistButton } from "@/components/watchlist/WatchlistButton";
import type { Stock } from "@/types";
import { LivePrice } from "./LivePrice";

export function StockHeader({ stock }: { stock: Stock }) {
  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-fg">{stock.symbol}</h1>
          {stock.sector && <Badge tone="brand">{stock.sector}</Badge>}
        </div>
        <p className="text-sm text-muted">{stock.company_name}</p>
        <LivePrice symbol={stock.symbol} />
      </div>
      <WatchlistButton symbol={stock.symbol} />
    </div>
  );
}
