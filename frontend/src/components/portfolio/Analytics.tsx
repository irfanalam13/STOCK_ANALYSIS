"use client";

import { Card, CardHeader } from "@/components/ui";
import type { PortfolioAnalytics } from "@/types";
import { formatCurrency } from "@/utils/format";

const BAR_COLORS = [
  "bg-brand", "bg-up", "bg-yellow-500", "bg-purple-500",
  "bg-pink-500", "bg-cyan-500", "bg-muted",
];

export function AllocationCard({ a }: { a: PortfolioAnalytics }) {
  return (
    <Card>
      <CardHeader title="Asset Allocation" subtitle="By sector" />
      {a.allocation.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted">No allocations yet.</p>
      ) : (
        <div className="space-y-3">
          {a.allocation.map((slice, i) => (
            <div key={slice.label}>
              <div className="mb-1 flex justify-between text-sm">
                <span className="text-fg">{slice.label}</span>
                <span className="tabular-nums text-muted">
                  {slice.pct}% · {formatCurrency(slice.value)}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
                <div
                  className={`h-full rounded-full ${BAR_COLORS[i % BAR_COLORS.length]}`}
                  style={{ width: `${Math.min(100, slice.pct)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export function RiskCard({ a }: { a: PortfolioAnalytics }) {
  const score = a.risk.score;
  const band = score >= 66 ? "High" : score >= 33 ? "Medium" : "Low";
  const tone = score >= 66 ? "text-down" : score >= 33 ? "text-yellow-500" : "text-up";
  const barTone = score >= 66 ? "bg-down" : score >= 33 ? "bg-yellow-500" : "bg-up";

  return (
    <Card>
      <CardHeader title="Risk Score" subtitle="Concentration · diversification · exposure" />
      <div className="flex items-end justify-between">
        <span className={`text-4xl font-bold tabular-nums ${tone}`}>{score}</span>
        <span className={`text-sm font-medium ${tone}`}>{band} risk</span>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-surface-2">
        <div className={`h-full rounded-full ${barTone}`} style={{ width: `${score}%` }} />
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs text-muted">
        <div><div className="text-fg">{a.risk.sectors}</div>sectors</div>
        <div><div className="text-fg">{a.risk.concentration}</div>concentration</div>
        <div><div className="text-fg">{Math.round(a.risk.exposure * 100)}%</div>invested</div>
      </div>
    </Card>
  );
}

export function PerformanceCard({ a }: { a: PortfolioAnalytics }) {
  return (
    <Card>
      <CardHeader title="Performance" subtitle="Trade statistics" />
      <div className="grid grid-cols-2 gap-3 text-sm">
        <Metric label="Win / Loss" value={`${a.win_trades} / ${a.loss_trades}`} />
        <Metric label="W/L Ratio" value={a.win_loss_ratio.toFixed(2)} />
        <Metric label="Total Trades" value={String(a.total_trades)} />
        <Metric
          label="ROI"
          value={`${a.roi >= 0 ? "+" : ""}${a.roi.toFixed(2)}%`}
          tone={a.roi >= 0 ? "up" : "down"}
        />
      </div>
    </Card>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "up" | "down" }) {
  const color = tone === "up" ? "text-up" : tone === "down" ? "text-down" : "text-fg";
  return (
    <div className="rounded-lg bg-surface-2 p-3">
      <p className="text-xs text-muted">{label}</p>
      <p className={`mt-0.5 text-lg font-semibold tabular-nums ${color}`}>{value}</p>
    </div>
  );
}
