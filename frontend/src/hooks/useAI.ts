"use client";

import { useQuery } from "@tanstack/react-query";

import { mlApi } from "@/services/api/ml.api";
import type { MarketDataPoint } from "@/types";
import { QUERY_KEYS } from "@/utils/constants";

/**
 * Fetch the fused AI signal for a symbol. Shared cache key, so the detail page
 * and the AI panel issue a single request between them. The latest history bar
 * is sent as the current feature vector when available.
 */
export function useAISignal(symbol: string, latest?: MarketDataPoint) {
  return useQuery({
    queryKey: QUERY_KEYS.aiSignal(symbol),
    queryFn: () => mlApi.signal(symbol, latest),
    enabled: Boolean(symbol),
    staleTime: 30_000,
    retry: 0, // ML is non-critical; don't hammer on failure
  });
}
