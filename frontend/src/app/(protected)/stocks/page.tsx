"use client";

import { useState } from "react";

import { StockTable } from "@/components/stocks/StockTable";
import { Card, Input, LoaderOverlay } from "@/components/ui";
import { useStocksWithQuotes } from "@/hooks/useStocks";

export default function StocksPage() {
  const { data, isLoading } = useStocksWithQuotes();
  const [query, setQuery] = useState("");

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-fg">Stocks</h1>
          <p className="text-sm text-muted">All listed NEPSE securities</p>
        </div>
        <div className="w-full sm:w-72">
          <Input
            placeholder="Filter by symbol or company…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <Card>
        {isLoading ? (
          <LoaderOverlay label="Loading stocks…" />
        ) : (
          <StockTable rows={data} query={query} />
        )}
      </Card>
    </div>
  );
}
