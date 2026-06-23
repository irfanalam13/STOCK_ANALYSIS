"use client";

import type { UTCTimestamp } from "lightweight-charts";

import { ChartContainer } from "@/components/charts/ChartContainer";
import { CHART_COLORS } from "@/components/charts/chartUtils";
import type { IndicatorPoint } from "@/types";

/** IndicatorPoint[] -> lightweight-charts line data (nulls dropped, deduped). */
function toLine(points: IndicatorPoint[]) {
  const byTime = new Map<number, number>();
  for (const p of points) {
    if (p.value == null) continue;
    byTime.set(Math.floor(new Date(p.timestamp).getTime() / 1000), p.value);
  }
  return [...byTime.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([time, value]) => ({ time: time as UTCTimestamp, value }));
}

export function TechnicalChart({
  series,
  height = 360,
}: {
  series: Record<string, IndicatorPoint[]>;
  height?: number;
}) {
  const close = toLine(series.close ?? []);
  const sma20 = toLine(series.sma_20 ?? []);
  const sma50 = toLine(series.sma_50 ?? []);
  const ema12 = toLine(series.ema_12 ?? []);
  const bUpper = toLine(series.bollinger_upper ?? []);
  const bLower = toLine(series.bollinger_lower ?? []);

  return (
    <ChartContainer
      height={height}
      deps={[close.length, close.at(-1)?.time]}
      onReady={(chart) => {
        chart.addAreaSeries({
          lineColor: CHART_COLORS.line,
          topColor: "rgba(59,130,246,0.35)",
          bottomColor: "rgba(59,130,246,0.02)",
          lineWidth: 2,
        }).setData(close);

        const overlay = (color: string, data: typeof close, lineWidth: 1 | 2 = 1) =>
          chart
            .addLineSeries({ color, lineWidth, priceLineVisible: false, lastValueVisible: false })
            .setData(data);

        overlay("#f59e0b", sma20);          // SMA20 — amber
        overlay("#a855f7", sma50);          // SMA50 — purple
        overlay("#22d3ee", ema12);          // EMA12 — cyan
        overlay("rgba(148,163,184,0.5)", bUpper);  // Bollinger bands — grey
        overlay("rgba(148,163,184,0.5)", bLower);
      }}
    />
  );
}
