"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  portfolioApi,
  type TransactionFilters,
} from "@/services/api/portfolio.api";
import type { TradeSide } from "@/types";
import { QUERY_KEYS } from "@/utils/constants";

export function usePortfolioSummary() {
  return useQuery({
    queryKey: QUERY_KEYS.portfolioSummary,
    queryFn: portfolioApi.summary,
    refetchInterval: 15_000, // re-value holdings against live prices
  });
}

export function usePortfolioAnalytics() {
  return useQuery({
    queryKey: QUERY_KEYS.portfolioAnalytics,
    queryFn: portfolioApi.analytics,
    refetchInterval: 30_000,
  });
}

export function usePortfolioTransactions(filters: TransactionFilters = {}) {
  return useQuery({
    queryKey: [...QUERY_KEYS.portfolioTransactions, filters],
    queryFn: () => portfolioApi.transactions(filters),
  });
}

export function useRiskSummary() {
  return useQuery({
    queryKey: QUERY_KEYS.portfolioRisk,
    queryFn: portfolioApi.riskSummary,
    refetchInterval: 45_000, // matches the backend risk cache TTL
  });
}

/** Buy/sell mutation that refreshes all portfolio views on success. */
export function useTrade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      side,
      symbol,
      quantity,
    }: {
      side: TradeSide;
      symbol: string;
      quantity: number;
    }) =>
      side === "BUY"
        ? portfolioApi.buy(symbol, quantity)
        : portfolioApi.sell(symbol, quantity),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.portfolioSummary });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.portfolioAnalytics });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.portfolioTransactions });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.portfolioRisk });
    },
  });
}
