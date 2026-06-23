"use client";

import {
  useEffect,
  useRef,
  type MutableRefObject,
} from "react";
import { createChart, type IChartApi } from "lightweight-charts";

import { baseChartOptions } from "./chartUtils";

interface ChartContainerProps {
  height?: number;
  /** Called once the chart is created; wire series here. */
  onReady: (chart: IChartApi) => void;
  /** Bump this to re-run onReady when the underlying data changes. */
  deps?: unknown[];
}

/**
 * Responsive wrapper that owns the lightweight-charts lifecycle: creation,
 * ResizeObserver-driven width, and teardown. Series are attached by the
 * caller via `onReady`, keeping this container fully reusable.
 */
export function ChartContainer({
  height = 320,
  onReady,
  deps = [],
}: ChartContainerProps) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef: MutableRefObject<IChartApi | null> = useRef(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      ...baseChartOptions,
      width: ref.current.clientWidth,
      height,
    });
    chartRef.current = chart;
    onReady(chart);
    chart.timeScale().fitContent();

    const observer = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w) chart.applyOptions({ width: Math.floor(w) });
    });
    observer.observe(ref.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [height, ...deps]);

  return <div ref={ref} className="w-full" style={{ height }} />;
}
