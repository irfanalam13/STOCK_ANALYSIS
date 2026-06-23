"use client";

import { useEffect, useState } from "react";

import { InsightList, SuggestionCard } from "@/components/analytics/Insights";
import { Card, CardHeader, Skeleton } from "@/components/ui";
import { useMarketInsights, useSymbolInsights } from "@/hooks/useAnalytics";
import { useStocks } from "@/hooks/useStocks";

export default function AIInsightsPage() {
  const { data: stocks } = useStocks();
  const [symbol, setSymbol] = useState("");

  useEffect(() => {
    if (!symbol && stocks && stocks.length > 0) setSymbol(stocks[0].symbol);
  }, [stocks, symbol]);

  const market = useMarketInsights();
  const symbolInsights = useSymbolInsights(symbol);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-fg">AI Insights</h1>
        <p className="text-sm text-muted">
          Natural-language market intelligence · probabilistic, not financial advice
        </p>
      </div>

      {market.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        <InsightList title="Market Intelligence" insights={market.data?.insights ?? []} />
      )}

      <Card>
        <CardHeader title="Per-Stock Analysis" />
        <select
          value={symbol}
          onChange={(e) => setSymbol(e.target.value)}
          className="rounded-md border border-border bg-surface px-3 py-1.5 text-sm text-fg"
        >
          {(stocks ?? []).map((s) => (
            <option key={s.symbol} value={s.symbol}>
              {s.symbol} — {s.company_name}
            </option>
          ))}
        </select>
      </Card>

      {symbolInsights.isLoading ? (
        <Skeleton className="h-40 w-full" />
      ) : symbolInsights.error ? (
        <Card>
          <p className="py-6 text-center text-muted">
            Not enough history for {symbol} insights yet.
          </p>
        </Card>
      ) : symbolInsights.data ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <InsightList
            title={`${symbolInsights.data.scope} Insights`}
            insights={symbolInsights.data.insights}
          />
          {symbolInsights.data.suggestion && (
            <SuggestionCard suggestion={symbolInsights.data.suggestion} />
          )}
        </div>
      ) : null}
    </div>
  );
}
