"use client";

import { useMemo } from "react";

import { GainersLosers } from "@/components/dashboard/GainersLosers";
import {
  IndexSummary,
  MarketOverviewCards,
} from "@/components/dashboard/MarketOverviewCards";
import { TrendingStocks } from "@/components/dashboard/TrendingStocks";
import {
  computeMarketStats,
  topByVolume,
  topGainers,
  topLosers,
} from "@/components/dashboard/dashboardData";
import { WatchlistPanel } from "@/components/watchlist/WatchlistPanel";
import { Skeleton } from "@/components/ui";
import { useStocksWithQuotes } from "@/hooks/useStocks";

export default function DashboardPage() {
  const { data, isLoading } = useStocksWithQuotes();

  const stats = useMemo(() => computeMarketStats(data), [data]);
  const gainers = useMemo(() => topGainers(data), [data]);
  const losers = useMemo(() => topLosers(data), [data]);
  const trending = useMemo(() => topByVolume(data), [data]);

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-28 w-full" />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-fg">Market Overview</h1>
        <p className="text-sm text-muted">Live NEPSE market snapshot</p>
      </div>

      <IndexSummary stats={stats} />
      <MarketOverviewCards stats={stats} />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <GainersLosers gainers={gainers} losers={losers} />
        </div>
        <div className="space-y-6">
          <TrendingStocks rows={trending} />
          <WatchlistPanel limit={5} />
        </div>
      </div>
    </div>
  );
}
