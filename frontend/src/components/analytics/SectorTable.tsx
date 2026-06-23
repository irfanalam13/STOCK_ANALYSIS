"use client";

import { Card, CardHeader } from "@/components/ui";
import type { SectorPerformance } from "@/types";
import { formatPercent, formatVolume } from "@/utils/format";

/** Diverging bar: green to the right for gains, red to the left for losses. */
function PerfBar({ pct, max }: { pct: number; max: number }) {
  const width = max > 0 ? Math.min(100, (Math.abs(pct) / max) * 100) : 0;
  const up = pct >= 0;
  return (
    <div className="flex h-3 w-full items-center">
      <div className="flex w-1/2 justify-end">
        {!up && <div className="h-3 rounded-l bg-down" style={{ width: `${width}%` }} />}
      </div>
      <div className="flex w-1/2 justify-start">
        {up && <div className="h-3 rounded-r bg-up" style={{ width: `${width}%` }} />}
      </div>
    </div>
  );
}

export function SectorTable({ rows }: { rows: SectorPerformance[] }) {
  const max = Math.max(1, ...rows.map((r) => Math.abs(r.avg_change_percent)));
  return (
    <Card>
      <CardHeader title="Sector Performance" subtitle="Ranked by average change" />
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-muted">
              <th className="py-2">Sector</th>
              <th className="py-2 text-right">Stocks</th>
              <th className="py-2 text-right">Avg Change</th>
              <th className="hidden py-2 md:table-cell">Strength</th>
              <th className="py-2 text-right">Rel. Strength</th>
              <th className="py-2 text-right">Turnover</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.sector} className="border-t border-border hover:bg-surface-2">
                <td className="py-2 font-medium text-fg">{r.sector}</td>
                <td className="py-2 text-right tabular-nums text-muted">{r.stocks}</td>
                <td
                  className={`py-2 text-right font-semibold tabular-nums ${
                    r.avg_change_percent >= 0 ? "text-up" : "text-down"
                  }`}
                >
                  {formatPercent(r.avg_change_percent)}
                </td>
                <td className="hidden w-40 py-2 md:table-cell">
                  <PerfBar pct={r.avg_change_percent} max={max} />
                </td>
                <td
                  className={`py-2 text-right tabular-nums ${
                    r.relative_strength >= 0 ? "text-up" : "text-down"
                  }`}
                >
                  {formatPercent(r.relative_strength)}
                </td>
                <td className="py-2 text-right tabular-nums text-muted">
                  {formatVolume(r.total_turnover)}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-muted">
                  No sector data — waiting for live market feed.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
