"use client";

import { Card } from "@/components/ui";
import type { MarketStats } from "./dashboardData";
import { formatNumber, formatPercent, formatVolume } from "@/utils/format";

function StatCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "up" | "down";
}) {
  const color =
    tone === "up" ? "text-up" : tone === "down" ? "text-down" : "text-fg";
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 text-2xl font-bold tabular-nums ${color}`}>{value}</p>
    </Card>
  );
}

export function MarketOverviewCards({ stats }: { stats: MarketStats }) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatCard label="Listed Stocks" value={formatNumber(stats.total)} />
      <StatCard label="Advancers" value={formatNumber(stats.advancers)} tone="up" />
      <StatCard label="Decliners" value={formatNumber(stats.decliners)} tone="down" />
      <StatCard label="Total Volume" value={formatVolume(stats.totalVolume)} />
    </div>
  );
}

export function IndexSummary({ stats }: { stats: MarketStats }) {
  const tone = stats.avgChangePct >= 0 ? "up" : "down";
  return (
    <Card className="bg-gradient-to-br from-surface to-surface-2">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted">NEPSE Index (synthetic)</p>
          <p className="mt-1 text-3xl font-bold tabular-nums text-fg">
            {formatNumber(stats.indexValue)}
          </p>
        </div>
        <div className={`text-right text-${tone}`}>
          <p className="text-2xl font-semibold">
            {formatPercent(stats.avgChangePct)}
          </p>
          <p className="text-xs text-muted">avg. change</p>
        </div>
      </div>
      <div className="mt-4 flex gap-4 text-sm">
        <span className="text-up">▲ {stats.advancers} up</span>
        <span className="text-down">▼ {stats.decliners} down</span>
        <span className="text-muted">• {stats.unchanged} flat</span>
      </div>
    </Card>
  );
}
