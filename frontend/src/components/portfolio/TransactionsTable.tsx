"use client";

import { Badge, Table, type Column } from "@/components/ui";
import type { PortfolioTransaction } from "@/types";
import { formatCurrency, formatDateTime } from "@/utils/format";

export function TransactionsTable({ rows }: { rows: PortfolioTransaction[] }) {
  const columns: Column<PortfolioTransaction>[] = [
    {
      key: "side",
      header: "Type",
      render: (t) => (
        <Badge tone={t.side === "BUY" ? "up" : "down"}>{t.side}</Badge>
      ),
    },
    {
      key: "symbol",
      header: "Symbol",
      render: (t) => (
        <div>
          <div className="font-medium text-fg">{t.symbol}</div>
          <div className="text-xs text-muted">{t.quantity} @ {formatCurrency(t.price)}</div>
        </div>
      ),
    },
    { key: "value", header: "Value", align: "right", render: (t) => formatCurrency(t.total_value) },
    { key: "fee", header: "Fee", align: "right", render: (t) => formatCurrency(t.fee) },
    {
      key: "pnl",
      header: "Realized",
      align: "right",
      render: (t) =>
        t.realized_pnl == null ? (
          <span className="text-muted">—</span>
        ) : (
          <span className={t.realized_pnl >= 0 ? "text-up" : "text-down"}>
            {formatCurrency(t.realized_pnl)}
          </span>
        ),
    },
    {
      key: "time",
      header: "Date",
      align: "right",
      render: (t) => <span className="text-muted">{formatDateTime(t.timestamp)}</span>,
    },
  ];

  return (
    <Table
      columns={columns}
      rows={rows}
      rowKey={(t) => t.id}
      emptyMessage="No transactions yet."
    />
  );
}
