"use client";

import { useEffect, useState } from "react";

import { SuggestionCard } from "@/components/analytics/Insights";
import { InsightList } from "@/components/analytics/Insights";
import { TechnicalChart } from "@/components/analytics/TechnicalChart";
import { Badge, Card, CardHeader, Skeleton } from "@/components/ui";
import { useTechnical } from "@/hooks/useAnalytics";
import { useStocks } from "@/hooks/useStocks";
import type { Timeframe } from "@/types";
import { formatNumber } from "@/utils/format";

const TIMEFRAMES: Timeframe[] = ["1D", "1W", "1M"];

function IndicatorStat({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="rounded-lg bg-surface-2 px-3 py-2">
      <p className="text-xs text-muted">{label}</p>
      <p className="text-sm font-semibold tabular-nums text-fg">{formatNumber(value)}</p>
    </div>
  );
}

export default function TechnicalPage() {
  const { data: stocks } = useStocks();
  const [symbol, setSymbol] = useState("");
  const [timeframe, setTimeframe] = useState<Timeframe>("1M");

  useEffect(() => {
    if (!symbol && stocks && stocks.length > 0) setSymbol(stocks[0].symbol);
  }, [stocks, symbol]);

  const { data, isLoading, error } = useTechnical(symbol, timeframe);
  const latest = data?.latest;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-fg">Technical Analysis</h1>
          <p className="text-sm text-muted">RSI · MACD · SMA · EMA · Bollinger Bands</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-fg"
          >
            {(stocks ?? []).map((s) => (
              <option key={s.symbol} value={s.symbol}>
                {s.symbol}
              </option>
            ))}
          </select>
          <div className="flex gap-1">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium ${
                  timeframe === tf
                    ? "bg-brand/15 text-brand"
                    : "bg-surface-2 text-muted hover:text-fg"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {isLoading ? (
        <Skeleton className="h-96 w-full" />
      ) : error ? (
        <Card>
          <p className="py-8 text-center text-muted">
            Not enough history to compute indicators for {symbol}.
          </p>
        </Card>
      ) : data ? (
        <>
          <Card>
            <CardHeader
              title={`${data.symbol} · ${data.timeframe}`}
              subtitle={`${data.points} data points`}
            />
            <TechnicalChart series={data.series} />
            <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted">
              <span><span className="text-[#3b82f6]">━</span> Price</span>
              <span><span className="text-[#f59e0b]">━</span> SMA20</span>
              <span><span className="text-[#a855f7]">━</span> SMA50</span>
              <span><span className="text-[#22d3ee]">━</span> EMA12</span>
              <span><span className="text-slate-400">━</span> Bollinger</span>
            </div>
          </Card>

          {latest && (
            <Card>
              <CardHeader title="Latest Indicators" />
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-6">
                <IndicatorStat label="RSI (14)" value={latest.rsi} />
                <IndicatorStat label="MACD" value={latest.macd} />
                <IndicatorStat label="Signal" value={latest.macd_signal} />
                <IndicatorStat label="SMA 20" value={latest.sma_20} />
                <IndicatorStat label="SMA 50" value={latest.sma_50} />
                <IndicatorStat label="EMA 12" value={latest.ema_12} />
              </div>
              {latest.signals.length > 0 && (
                <div className="mt-4 flex flex-wrap gap-2">
                  {latest.signals.map((sig, i) => (
                    <Badge
                      key={i}
                      tone={sig.signal === "BUY" ? "up" : sig.signal === "SELL" ? "down" : "neutral"}
                    >
                      {sig.indicator}: {sig.note}
                    </Badge>
                  ))}
                </div>
              )}
            </Card>
          )}

          <div className="grid gap-6 lg:grid-cols-2">
            <InsightList title={`${data.symbol} Insights`} insights={data.insights} />
            <SuggestionCard suggestion={data.suggestion} />
          </div>
        </>
      ) : null}
    </div>
  );
}
