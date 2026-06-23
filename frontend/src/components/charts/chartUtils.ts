import type { UTCTimestamp } from "lightweight-charts";

import type { MarketDataPoint } from "@/types";

export const CHART_COLORS = {
  up: "#16a34a",
  down: "#dc2626",
  line: "#3b82f6",
  grid: "rgba(148, 163, 184, 0.15)",
  text: "#94a3b8",
};

/** Shared layout/grid options so every chart looks consistent. */
export const baseChartOptions = {
  layout: {
    background: { color: "transparent" },
    textColor: CHART_COLORS.text,
    fontFamily: "inherit",
  },
  grid: {
    vertLines: { color: CHART_COLORS.grid },
    horzLines: { color: CHART_COLORS.grid },
  },
  rightPriceScale: { borderColor: CHART_COLORS.grid },
  timeScale: { borderColor: CHART_COLORS.grid, timeVisible: true },
  autoSize: false,
};

function toUnix(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

/**
 * lightweight-charts requires strictly ascending, unique time values. Quotes
 * generated within the same second are de-duplicated keeping the latest.
 */
export function toCandles(points: MarketDataPoint[]) {
  const byTime = new Map<number, MarketDataPoint>();
  for (const p of points) byTime.set(toUnix(p.timestamp), p);
  return [...byTime.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([time, p]) => ({
      time: time as UTCTimestamp,
      open: Number(p.open_price),
      high: Number(p.high_price),
      low: Number(p.low_price),
      close: Number(p.close_price),
    }));
}

export function toLine(points: MarketDataPoint[]) {
  const byTime = new Map<number, number>();
  for (const p of points) byTime.set(toUnix(p.timestamp), Number(p.close_price));
  return [...byTime.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([time, value]) => ({ time: time as UTCTimestamp, value }));
}

export function toVolume(points: MarketDataPoint[]) {
  const byTime = new Map<number, MarketDataPoint>();
  for (const p of points) byTime.set(toUnix(p.timestamp), p);
  return [...byTime.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([time, p]) => ({
      time: time as UTCTimestamp,
      value: Number(p.volume),
      color:
        Number(p.close_price) >= Number(p.open_price)
          ? "rgba(22,163,74,0.5)"
          : "rgba(220,38,38,0.5)",
    }));
}
