"use client";

import type { MarketDataPoint } from "@/types";
import { ChartContainer } from "./ChartContainer";
import { toVolume } from "./chartUtils";

export function VolumeChart({
  data,
  height = 160,
}: {
  data: MarketDataPoint[];
  height?: number;
}) {
  const volume = toVolume(data);

  return (
    <ChartContainer
      height={height}
      deps={[volume.length, volume.at(-1)?.time]}
      onReady={(chart) => {
        const series = chart.addHistogramSeries({
          priceFormat: { type: "volume" },
          priceScaleId: "",
        });
        series.priceScale().applyOptions({
          scaleMargins: { top: 0.1, bottom: 0 },
        });
        series.setData(volume);
      }}
    />
  );
}
