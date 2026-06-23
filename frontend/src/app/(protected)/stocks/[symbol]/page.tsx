"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { AIPanel } from "@/components/ai/AIPanel";
import { TradeModal } from "@/components/portfolio/TradeModal";
import { CandlestickChart } from "@/components/charts/CandlestickChart";
import { LineChart } from "@/components/charts/LineChart";
import { VolumeChart } from "@/components/charts/VolumeChart";
import { CompanyInfo } from "@/components/stocks/CompanyInfo";
import { StockHeader } from "@/components/stocks/StockHeader";
import { Button, Card, CardHeader, LoaderOverlay } from "@/components/ui";
import { useAISignal } from "@/hooks/useAI";
import { useStock, useStockHistory } from "@/hooks/useStocks";
import { ROUTES } from "@/utils/constants";

type ChartMode = "candles" | "line";

export default function StockDetailPage() {
  const params = useParams<{ symbol: string }>();
  const symbol = decodeURIComponent(params.symbol).toUpperCase();
  const [mode, setMode] = useState<ChartMode>("candles");
  const [tradeOpen, setTradeOpen] = useState(false);

  const { data: stock, isLoading, isError } = useStock(symbol);
  const { data: history = [] } = useStockHistory(symbol, 300);
  const latest = history.at(-1);
  // Shared cache with AIPanel — used here only for the chart overlay.
  const { data: ai } = useAISignal(symbol, latest);

  if (isLoading) return <LoaderOverlay label={`Loading ${symbol}…`} />;
  if (isError || !stock) {
    return (
      <Card className="text-center">
        <p className="text-fg">Stock “{symbol}” not found.</p>
        <Link href={ROUTES.stocks} className="mt-2 inline-block text-brand hover:underline">
          ← Back to stocks
        </Link>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Link href={ROUTES.stocks} className="text-sm text-muted hover:text-fg">
        ← All stocks
      </Link>

      <Card>
        <StockHeader stock={stock} />
        <div className="mt-4 flex justify-end">
          <Button onClick={() => setTradeOpen(true)}>Trade {symbol}</Button>
        </div>
      </Card>

      <TradeModal
        open={tradeOpen}
        onClose={() => setTradeOpen(false)}
        presetSymbol={symbol}
      />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader
              title="Price Chart"
              action={
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant={mode === "candles" ? "primary" : "ghost"}
                    onClick={() => setMode("candles")}
                  >
                    Candles
                  </Button>
                  <Button
                    size="sm"
                    variant={mode === "line" ? "primary" : "ghost"}
                    onClick={() => setMode("line")}
                  >
                    Line
                  </Button>
                </div>
              }
            />
            {history.length === 0 ? (
              <p className="py-16 text-center text-sm text-muted">
                No history yet — data populates as the pipeline runs.
              </p>
            ) : mode === "candles" ? (
              <CandlestickChart
                data={history}
                symbol={symbol}
                predictedPrice={ai?.details.predicted_price ?? null}
              />
            ) : (
              <LineChart data={history} />
            )}
          </Card>

          <Card>
            <CardHeader title="Volume" />
            {history.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted">No data yet.</p>
            ) : (
              <VolumeChart data={history} />
            )}
          </Card>
        </div>

        <div className="space-y-6">
          <AIPanel symbol={symbol} latest={latest} />
          <CompanyInfo stock={stock} latest={latest} />
        </div>
      </div>
    </div>
  );
}
