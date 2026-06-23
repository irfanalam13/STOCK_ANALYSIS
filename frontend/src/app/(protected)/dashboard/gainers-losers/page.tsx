"use client";

import { useState } from "react";

import { MoversTable } from "@/components/analytics/MoversTable";
import { Card } from "@/components/ui";
import { useMovers } from "@/hooks/useAnalytics";

const VOLUME_FILTERS = [
  { label: "All", value: 0 },
  { label: "≥ 5K", value: 5_000 },
  { label: "≥ 25K", value: 25_000 },
  { label: "≥ 100K", value: 100_000 },
];

export default function GainersLosersPage() {
  const [minVolume, setMinVolume] = useState(0);
  const [top, setTop] = useState(10);

  const gainers = useMovers("gainers", top, minVolume);
  const losers = useMovers("losers", top, minVolume);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-fg">Top Gainers & Losers</h1>
        <p className="text-sm text-muted">Liquidity-aware ranking with volume filters</p>
      </div>

      <Card className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted">Min volume:</span>
          {VOLUME_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setMinVolume(f.value)}
              className={`rounded-md px-3 py-1 text-sm font-medium ${
                minVolume === f.value
                  ? "bg-brand/15 text-brand"
                  : "bg-surface-2 text-muted hover:text-fg"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted">Show:</span>
          {[10, 20, 50].map((n) => (
            <button
              key={n}
              onClick={() => setTop(n)}
              className={`rounded-md px-3 py-1 text-sm font-medium ${
                top === n ? "bg-brand/15 text-brand" : "bg-surface-2 text-muted hover:text-fg"
              }`}
            >
              Top {n}
            </button>
          ))}
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <MoversTable title="Top Gainers" rows={gainers.data ?? []} variant="gainers" />
        <MoversTable title="Top Losers" rows={losers.data ?? []} variant="losers" />
      </div>
    </div>
  );
}
