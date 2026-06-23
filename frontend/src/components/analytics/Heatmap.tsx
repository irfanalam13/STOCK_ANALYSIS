"use client";

import { useRouter } from "next/navigation";
import { useMemo } from "react";

import type { HeatmapTile } from "@/types";
import { ROUTES } from "@/utils/constants";
import { formatCurrency, formatPercent, formatVolume } from "@/utils/format";

/** Map a % change to a Bloomberg-style green/red shade (clamped at ±5%). */
function tileColor(pct: number): string {
  const mag = Math.min(1, Math.abs(pct) / 5);
  const alpha = 0.12 + mag * 0.6;
  return pct >= 0
    ? `rgba(22, 163, 74, ${alpha.toFixed(2)})`
    : `rgba(220, 38, 38, ${alpha.toFixed(2)})`;
}

export function Heatmap({
  tiles,
  mode,
}: {
  tiles: HeatmapTile[];
  mode: "change" | "volume";
}) {
  const router = useRouter();

  const grouped = useMemo(() => {
    const map = new Map<string, HeatmapTile[]>();
    for (const t of tiles) {
      const list = map.get(t.sector) ?? [];
      list.push(t);
      map.set(t.sector, list);
    }
    return [...map.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [tiles]);

  if (tiles.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-surface p-10 text-center text-muted">
        No heatmap data — waiting for live market feed.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {grouped.map(([sector, members]) => (
        <div key={sector}>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
            {sector}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {members.map((t) => (
              <button
                key={t.symbol}
                onClick={() => router.push(ROUTES.stock(t.symbol))}
                title={`${t.symbol}\nPrice: ${formatCurrency(t.price)}\nChange: ${formatPercent(
                  t.change_percent,
                )}\nVolume: ${formatVolume(t.volume)}`}
                className="flex flex-col items-center justify-center rounded-md px-3 py-2 text-center transition-transform hover:scale-[1.04]"
                style={{
                  backgroundColor: tileColor(t.change_percent),
                  flexBasis: 84,
                  flexGrow: mode === "volume" ? Math.max(0.2, t.weight * members.length) : 0,
                }}
              >
                <span className="text-sm font-bold text-fg">{t.symbol}</span>
                <span
                  className={`text-xs font-semibold tabular-nums ${
                    t.change_percent >= 0 ? "text-up" : "text-down"
                  }`}
                >
                  {formatPercent(t.change_percent)}
                </span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
