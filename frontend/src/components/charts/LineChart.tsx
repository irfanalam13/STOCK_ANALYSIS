"use client";

import type { MarketDataPoint } from "@/types";
import { ChartContainer } from "./ChartContainer";
import { CHART_COLORS, toLine } from "./chartUtils";

export function LineChart({
  data,
  height = 280,
}: {
  data: MarketDataPoint[];
  height?: number;
}) {
  const line = toLine(data);

  return (
    <ChartContainer
      height={height}
      deps={[line.length, line.at(-1)?.time]}
      onReady={(chart) => {
        const series = chart.addAreaSeries({
          lineColor: CHART_COLORS.line,
          topColor: "rgba(59,130,246,0.4)",
          bottomColor: "rgba(59,130,246,0.02)",
          lineWidth: 2,
        });
        series.setData(line);
      }}
    />
  );
}
