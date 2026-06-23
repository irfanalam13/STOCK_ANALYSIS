"use client";

import { Card } from "@/components/ui";
import type { PortfolioSummary } from "@/types";
import { formatCurrency, formatPercent } from "@/utils/format";

function Stat({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "up" | "down";
}) {
  const color = tone === "up" ? "text-up" : tone === "down" ? "text-down" : "text-fg";
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-bold tabular-nums ${color}`}>{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted">{sub}</p>}
    </Card>
  );
}

export function SummaryCards({ s }: { s: PortfolioSummary }) {
  const pnlTone = s.total_pnl >= 0 ? "up" : "down";
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Stat label="Total Value" value={formatCurrency(s.total_value)}
            sub={`Invested ${formatCurrency(s.holdings_value)}`} />
      <Stat label="Cash" value={formatCurrency(s.cash_balance)}
            sub={`of ${formatCurrency(s.initial_balance)}`} />
      <Stat label="Total P/L" value={formatCurrency(s.total_pnl)} tone={pnlTone}
            sub={`ROI ${formatPercent(s.roi)}`} />
      <Stat label="Unrealized / Realized"
            value={formatCurrency(s.total_unrealized_pnl)}
            tone={s.total_unrealized_pnl >= 0 ? "up" : "down"}
            sub={`Realized ${formatCurrency(s.total_realized_pnl)}`} />
    </div>
  );
}
