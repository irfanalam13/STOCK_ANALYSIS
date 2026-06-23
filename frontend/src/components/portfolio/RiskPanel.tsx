"use client";

import { Badge, Card, CardHeader, Skeleton } from "@/components/ui";
import { useRiskSummary } from "@/hooks/usePortfolio";

/** AI-driven portfolio risk panel: overall score, risky assets, warnings. */
export function RiskPanel() {
  const { data, isLoading } = useRiskSummary();

  if (isLoading) {
    return (
      <Card>
        <CardHeader title="🛡️ Risk Analysis" />
        <Skeleton className="h-24 w-full" />
      </Card>
    );
  }
  if (!data) return null;

  const score = data.portfolio_risk_score;
  const band = score >= 66 ? "High" : score >= 33 ? "Medium" : "Low";
  const tone = score >= 66 ? "text-down" : score >= 33 ? "text-yellow-500" : "text-up";
  const barTone = score >= 66 ? "bg-down" : score >= 33 ? "bg-yellow-500" : "bg-up";

  return (
    <Card>
      <CardHeader title="🛡️ Risk Analysis" subtitle="AI-enhanced (volatility + signals)" />

      <div className="flex items-end justify-between">
        <span className={`text-4xl font-bold tabular-nums ${tone}`}>{score}</span>
        <span className={`text-sm font-medium ${tone}`}>{band} risk</span>
      </div>
      <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-surface-2">
        <div className={`h-full rounded-full ${barTone}`} style={{ width: `${score}%` }} />
      </div>

      {data.high_risk_holdings.length > 0 && (
        <div className="mt-4">
          <p className="mb-1 text-xs font-medium text-muted">High-risk holdings</p>
          <div className="flex flex-wrap gap-1.5">
            {data.high_risk_holdings.map((s) => (
              <Badge key={s} tone="down">🔴 {s}</Badge>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 space-y-2">
        {data.warnings.map((w, i) => (
          <div
            key={i}
            className="flex items-start gap-2 rounded-lg bg-surface-2 px-3 py-2 text-sm text-fg"
          >
            <span>⚠️</span>
            <span>{w}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
