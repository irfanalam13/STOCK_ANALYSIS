"use client";

import {
  createChart,
  LineStyle,
  type CandlestickData,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import { useMarketStore } from "@/store/market.store";
import type { MarketDataPoint } from "@/types";
import { baseChartOptions, CHART_COLORS, toCandles } from "./chartUtils";

/**
 * Candlestick chart with two update paths:
 *
 * 1. `setData` once for the historical series (on data identity change).
 * 2. `series.update()` for each live OHLC candle pushed into the market store —
 *    an incremental patch, not a full re-render, so the chart stays smooth
 *    under high-frequency updates.
 */
export function CandlestickChart({
  data,
  symbol,
  predictedPrice,
  height = 360,
}: {
  data: MarketDataPoint[];
  symbol?: string;
  predictedPrice?: number | null;
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const priceLineRef = useRef<IPriceLine | null>(null);
  const lastTimeRef = useRef<number>(0);

  // Live candle for this symbol (selector → re-renders only on its change).
  const liveCandle = useMarketStore((s) =>
    symbol ? s.candles[symbol] : undefined,
  );

  // ---- create chart + load historical series ----
  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      ...baseChartOptions,
      width: containerRef.current.clientWidth,
      height,
    });
    const series = chart.addCandlestickSeries({
      upColor: CHART_COLORS.up,
      downColor: CHART_COLORS.down,
      borderUpColor: CHART_COLORS.up,
      borderDownColor: CHART_COLORS.down,
      wickUpColor: CHART_COLORS.up,
      wickDownColor: CHART_COLORS.down,
    });
    const candles = toCandles(data);
    series.setData(candles);
    chart.timeScale().fitContent();
    lastTimeRef.current = (candles.at(-1)?.time as number) ?? 0;

    chartRef.current = chart;
    seriesRef.current = series;

    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w) chart.applyOptions({ width: Math.floor(w) });
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, height]);

  // ---- incremental live patch ----
  useEffect(() => {
    if (!liveCandle || !seriesRef.current) return;
    const time = Math.floor(
      new Date(liveCandle.timestamp).getTime() / 1000,
    ) as UTCTimestamp;
    // lightweight-charts rejects updates older than the last bar — guard it.
    if ((time as number) < lastTimeRef.current) return;
    const bar: CandlestickData = {
      time,
      open: liveCandle.open,
      high: liveCandle.high,
      low: liveCandle.low,
      close: liveCandle.close,
    };
    seriesRef.current.update(bar);
    lastTimeRef.current = time as number;
  }, [liveCandle]);

  // ---- AI predicted-price overlay (dashed price line) ----
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;
    if (priceLineRef.current) {
      series.removePriceLine(priceLineRef.current);
      priceLineRef.current = null;
    }
    if (predictedPrice != null) {
      priceLineRef.current = series.createPriceLine({
        price: predictedPrice,
        color: "#a855f7",
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: "AI",
      });
    }
  }, [predictedPrice, data]);

  return <div ref={containerRef} className="w-full" style={{ height }} />;
}
