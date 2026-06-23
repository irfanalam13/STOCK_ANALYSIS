"use client";

import { Badge, Card, CardHeader, Skeleton } from "@/components/ui";
import { useAISignal } from "@/hooks/useAI";
import type { MarketDataPoint } from "@/types";
import { formatCurrency, formatPercent } from "@/utils/format";
import { ConfidenceMeter } from "./ConfidenceMeter";
import { SignalBadge } from "./SignalBadge";

const TREND_TONE = {
  UPTREND: { tone: "up" as const, arrow: "▲" },
  DOWNTREND: { tone: "down" as const, arrow: "▼" },
  SIDEWAYS: { tone: "neutral" as const, arrow: "→" },
};

const VOL_TONE = {
  LOW: "up" as const,
  MEDIUM: "neutral" as const,
  HIGH: "down" as const,
};

export function AIPanel({
  symbol,
  latest,
}: {
  symbol: string;
  latest?: MarketDataPoint;
}) {
  const { data, isLoading, isError } = useAISignal(symbol, latest);

  return (
    <Card>
      <CardHeader
        title="🤖 AI Insights"
        subtitle="Price · trend · volatility · signal"
        action={
          data?.details.fallback ? (
            <Badge tone="neutral">heuristic</Badge>
          ) : data ? (
            <Badge tone="brand">model</Badge>
          ) : null
        }
      />

      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-9 w-32" />
          <Skeleton className="h-2 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : isError || !data ? (
        <p className="py-6 text-center text-sm text-muted">
          AI service unavailable.
        </p>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <SignalBadge signal={data.signal} strength={data.strength} />
            <div className="text-right">
              <p className="text-xs text-muted">Predicted</p>
              <p className="font-bold tabular-nums text-fg">
                {formatCurrency(data.details.predicted_price)}
              </p>
              <p
                className={`text-xs tabular-nums ${
                  data.details.predicted_return >= 0 ? "text-up" : "text-down"
                }`}
              >
                {formatPercent(data.details.predicted_return * 100)}
              </p>
            </div>
          </div>

          <ConfidenceMeter value={data.confidence} />

          <div className="flex gap-2">
            <Badge tone={TREND_TONE[data.details.trend].tone}>
              {TREND_TONE[data.details.trend].arrow} {data.details.trend}
            </Badge>
            <Badge tone={VOL_TONE[data.details.volatility]}>
              {data.details.volatility} volatility
            </Badge>
          </div>

          <div>
            <p className="mb-1 text-xs font-medium text-muted">Why</p>
            <ul className="space-y-1">
              {data.reason.map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-fg">
                  <span className="text-brand">•</span>
                  {r}
                </li>
              ))}
            </ul>
          </div>

          <p className="text-[11px] text-muted">
            Informational only — not financial advice.
          </p>
        </div>
      )}
    </Card>
  );
}
