"use client";

import { IndexHero, OverviewStats } from "@/components/analytics/OverviewCards";
import { InsightList } from "@/components/analytics/Insights";
import { MoversTable } from "@/components/analytics/MoversTable";
import { SectorTable } from "@/components/analytics/SectorTable";
import { Skeleton } from "@/components/ui";
import {
  useMarketInsights,
  useMovers,
  useOverview,
  useSectors,
} from "@/hooks/useAnalytics";

export default function AnalyticsOverviewPage() {
  const overview = useOverview();
  const sectors = useSectors();
  const gainers = useMovers("gainers", 5);
  const losers = useMovers("losers", 5);
  const insights = useMarketInsights();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-fg">Market Overview</h1>
        <p className="text-sm text-muted">
          Institutional-grade live snapshot of the NEPSE market
        </p>
      </div>

      {overview.isLoading || !overview.data ? (
        <Skeleton className="h-40 w-full" />
      ) : (
        <>
          <IndexHero data={overview.data} />
          <OverviewStats data={overview.data} />
        </>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <MoversTable title="Top Gainers" rows={gainers.data ?? []} variant="gainers" />
        <MoversTable title="Top Losers" rows={losers.data ?? []} variant="losers" />
      </div>

      <SectorTable rows={sectors.data ?? []} />

      <InsightList title="AI Market Insights" insights={insights.data?.insights ?? []} />
    </div>
  );
}
