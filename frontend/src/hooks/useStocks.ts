"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";

import { marketApi } from "@/services/api/market.api";
import { stocksApi } from "@/services/api/stocks.api";
import { useMarketStore } from "@/store/market.store";
import type { StockWithQuote } from "@/types";
import { QUERY_KEYS } from "@/utils/constants";
import { enrichStocks } from "@/utils/helpers";

/** The stock catalog (cached server-side; rarely changes). */
export function useStocks() {
  return useQuery({
    queryKey: QUERY_KEYS.stocks,
    queryFn: stocksApi.list,
    staleTime: 5 * 60 * 1000,
  });
}

/** A single stock's metadata. */
export function useStock(symbol: string) {
  return useQuery({
    queryKey: QUERY_KEYS.stock(symbol),
    queryFn: () => stocksApi.get(symbol),
    enabled: Boolean(symbol),
  });
}

/** A stock's OHLCV history (oldest→newest for charting). */
export function useStockHistory(symbol: string, limit = 200) {
  return useQuery({
    queryKey: [...QUERY_KEYS.history(symbol), limit],
    queryFn: () => stocksApi.history(symbol, limit),
    enabled: Boolean(symbol),
    select: (rows) =>
      [...rows].sort(
        (a, b) =>
          new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      ),
  });
}

/** Initial live snapshot from Redis (WebSocket then keeps it fresh). */
export function useLiveSnapshot() {
  return useQuery({
    queryKey: QUERY_KEYS.live,
    queryFn: marketApi.live,
    refetchInterval: 30_000, // safety net if the socket drops
  });
}

/** Catalog joined with live quotes from the market store — table-ready. */
export function useStocksWithQuotes(): {
  data: StockWithQuote[];
  isLoading: boolean;
} {
  const { data: stocks, isLoading } = useStocks();
  const quotes = useMarketStore((s) => s.quotes);

  const data = useMemo(
    () => (stocks ? enrichStocks(stocks, quotes) : []),
    [stocks, quotes],
  );

  return { data, isLoading };
}
