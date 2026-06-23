"use client";

import { useRouter } from "next/navigation";

import { PriceChange } from "@/components/stocks/PriceChange";
import { RiskBadge } from "@/components/portfolio/RiskBadge";
import { Button, Table, type Column } from "@/components/ui";
import type { Holding } from "@/types";
import { ROUTES } from "@/utils/constants";
import { formatCurrency } from "@/utils/format";

export function HoldingsTable({
  holdings,
  onSell,
}: {
  holdings: Holding[];
  onSell: (symbol: string) => void;
}) {
  const router = useRouter();

  const columns: Column<Holding>[] = [
    {
      key: "symbol",
      header: "Symbol",
      render: (h) => (
        <div>
          <div className="font-semibold text-fg">{h.symbol}</div>
          <div className="text-xs text-muted">{h.quantity} sh @ {formatCurrency(h.avg_buy_price)}</div>
        </div>
      ),
    },
    { key: "current", header: "Price", align: "right", render: (h) => formatCurrency(h.current_price) },
    { key: "value", header: "Value", align: "right", render: (h) => formatCurrency(h.market_value) },
    {
      key: "pnl",
      header: "Unrealized",
      align: "right",
      render: (h) => (
        <div className="flex flex-col items-end">
          <span className={h.unrealized_pnl >= 0 ? "text-up" : "text-down"}>
            {formatCurrency(h.unrealized_pnl)}
          </span>
          <PriceChange pct={h.unrealized_pct} />
        </div>
      ),
    },
    {
      key: "risk",
      header: "Risk",
      align: "right",
      render: (h) => <RiskBadge risk={h.risk} />,
    },
    {
      key: "actions",
      header: "",
      align: "right",
      render: (h) => (
        <Button size="sm" variant="secondary" onClick={(e) => { e.stopPropagation(); onSell(h.symbol); }}>
          Sell
        </Button>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      rows={holdings}
      rowKey={(h) => h.symbol}
      onRowClick={(h) => router.push(ROUTES.stock(h.symbol))}
      emptyMessage="No holdings yet. Buy a stock to get started."
    />
  );
}
