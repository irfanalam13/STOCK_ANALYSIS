"use client";

import { ConfidenceMeter } from "@/components/ai/ConfidenceMeter";
import { Badge, Card } from "@/components/ui";
import type { MarketOverview } from "@/types";
import { formatNumber, formatPercent, formatVolume } from "@/utils/format";

function Stat({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  const color = tone === "up" ? "text-up" : tone === "down" ? "text-down" : "text-fg";
  return (
    <Card>
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-1 text-xl font-bold tabular-nums ${color}`}>{value}</p>
    </Card>
  );
}

export function IndexHero({ data }: { data: MarketOverview }) {
  const up = data.index_change_percent >= 0;
  const tone =
    data.sentiment === "Bullish" ? "up" : data.sentiment === "Bearish" ? "down" : "neutral";
  return (
    <Card className="bg-gradient-to-br from-surface to-surface-2">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm text-muted">NEPSE Index (turnover-weighted proxy)</p>
          <p className="mt-1 text-4xl font-bold tabular-nums text-fg">
            {formatNumber(data.index_value)}
          </p>
          <p className={`mt-1 text-lg font-semibold ${up ? "text-up" : "text-down"}`}>
            {up ? "▲" : "▼"} {formatPercent(data.index_change_percent)}
          </p>
        </div>
        <div className="min-w-[180px] space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted">Sentiment</span>
            <Badge tone={tone}>{data.sentiment}</Badge>
          </div>
          <ConfidenceMeter value={data.sentiment_score / 100} label="Market sentiment" />
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-4 text-sm">
        <span className="text-up">▲ {data.advancers} advancing</span>
        <span className="text-down">▼ {data.decliners} declining</span>
        <span className="text-muted">• {data.unchanged} unchanged</span>
      </div>
    </Card>
  );
}

export function OverviewStats({ data }: { data: MarketOverview }) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <Stat label="Listed Stocks" value={formatNumber(data.total_stocks)} />
      <Stat
        label="Avg Change"
        value={formatPercent(data.avg_change_percent)}
        tone={data.avg_change_percent >= 0 ? "up" : "down"}
      />
      <Stat label="Total Volume" value={formatVolume(data.total_volume)} />
      <Stat label="Turnover (Rs)" value={formatVolume(data.total_turnover)} />
    </div>
  );
}
