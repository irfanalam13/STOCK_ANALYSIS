"use client";

import { useRouter } from "next/navigation";

import { PriceChange } from "@/components/stocks/PriceChange";
import { Button, Card, Table, type Column } from "@/components/ui";
import { useStocksWithQuotes } from "@/hooks/useStocks";
import { useWatchlist } from "@/hooks/useWatchlist";
import type { StockWithQuote } from "@/types";
import { ROUTES } from "@/utils/constants";
import { formatCurrency, formatVolume } from "@/utils/format";

export default function WatchlistPage() {
  const router = useRouter();
  const { symbols, remove } = useWatchlist();
  const { data } = useStocksWithQuotes();
  const rows = data.filter((s) => symbols.includes(s.symbol));

  const columns: Column<StockWithQuote>[] = [
    {
      key: "symbol",
      header: "Symbol",
      render: (r) => (
        <div>
          <div className="font-semibold text-fg">{r.symbol}</div>
          <div className="text-xs text-muted">{r.company_name}</div>
        </div>
      ),
    },
    {
      key: "price",
      header: "Price",
      align: "right",
      render: (r) => formatCurrency(r.price),
    },
    {
      key: "change",
      header: "Change %",
      align: "right",
      render: (r) => <PriceChange pct={r.changePct} />,
    },
    {
      key: "volume",
      header: "Volume",
      align: "right",
      render: (r) => formatVolume(r.volume),
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (r) => (
        <Button
          size="sm"
          variant="ghost"
          onClick={(e) => {
            e.stopPropagation();
            remove(r.symbol);
          }}
        >
          Remove
        </Button>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-fg">Watchlist</h1>
        <p className="text-sm text-muted">
          {symbols.length} tracked symbol{symbols.length === 1 ? "" : "s"}
        </p>
      </div>

      <Card>
        {symbols.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-muted">Your watchlist is empty.</p>
            <Button className="mt-3" onClick={() => router.push(ROUTES.stocks)}>
              Browse stocks
            </Button>
          </div>
        ) : (
          <Table
            columns={columns}
            rows={rows}
            rowKey={(r) => r.id}
            onRowClick={(r) => router.push(ROUTES.stock(r.symbol))}
          />
        )}
      </Card>
    </div>
  );
}
