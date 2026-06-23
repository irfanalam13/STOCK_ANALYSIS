"use client";

import { useState } from "react";

import { Heatmap } from "@/components/analytics/Heatmap";
import { Card, Skeleton } from "@/components/ui";
import { useHeatmap } from "@/hooks/useAnalytics";

export default function HeatmapPage() {
  const [mode, setMode] = useState<"change" | "volume">("change");
  const { data, isLoading } = useHeatmap(mode);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-fg">Market Heatmap</h1>
          <p className="text-sm text-muted">
            Color-coded performance · click a tile to drill down
          </p>
        </div>
        <div className="flex gap-2">
          {(["change", "volume"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium capitalize ${
                mode === m ? "bg-brand/15 text-brand" : "bg-surface-2 text-muted hover:text-fg"
              }`}
            >
              {m === "volume" ? "Volume-weighted" : "Equal"}
            </button>
          ))}
        </div>
      </div>

      <Card>
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : (
          <Heatmap tiles={data ?? []} mode={mode} />
        )}
      </Card>
    </div>
  );
}
