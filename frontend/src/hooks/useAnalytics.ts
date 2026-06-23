"use client";

import { useQuery } from "@tanstack/react-query";

import { analyticsApi } from "@/services/api/analytics.api";
import type { Timeframe } from "@/types";
import { QUERY_KEYS } from "@/utils/constants";

// Live aggregations are cheap and cached server-side; poll as a socket-drop
// safety net. The backend caches for a few seconds, so this stays sub-second.
const LIVE_REFETCH = 15_000;

export function useOverview() {
  return useQuery({
    queryKey: QUERY_KEYS.analyticsOverview,
    queryFn: analyticsApi.overview,
    refetchInterval: LIVE_REFETCH,
  });
}

export function useSectors() {
  return useQuery({
    queryKey: QUERY_KEYS.analyticsSectors,
    queryFn: analyticsApi.sectors,
    refetchInterval: LIVE_REFETCH,
  });
}

export function useMovers(
  direction: "gainers" | "losers",
  top = 10,
  minVolume = 0,
) {
  return useQuery({
    queryKey: QUERY_KEYS.analyticsMovers(direction, top, minVolume),
    queryFn: () => analyticsApi.movers(direction, top, minVolume),
    refetchInterval: LIVE_REFETCH,
  });
}

export function useHeatmap(
  mode: "change" | "volume" = "change",
  sector: string | null = null,
) {
  return useQuery({
    queryKey: QUERY_KEYS.analyticsHeatmap(mode, sector),
    queryFn: () => analyticsApi.heatmap(mode, sector),
    refetchInterval: LIVE_REFETCH,
  });
}

export function useTechnical(symbol: string, timeframe: Timeframe = "1M") {
  return useQuery({
    queryKey: QUERY_KEYS.analyticsTechnical(symbol, timeframe),
    queryFn: () => analyticsApi.technical(symbol, timeframe),
    enabled: Boolean(symbol),
  });
}

export function useMarketInsights() {
  return useQuery({
    queryKey: QUERY_KEYS.analyticsAI("market"),
    queryFn: analyticsApi.marketInsights,
    refetchInterval: 30_000,
  });
}

export function useSymbolInsights(symbol: string, timeframe: Timeframe = "1M") {
  return useQuery({
    queryKey: [...QUERY_KEYS.analyticsAI(symbol), timeframe],
    queryFn: () => analyticsApi.symbolInsights(symbol, timeframe),
    enabled: Boolean(symbol),
  });
}
