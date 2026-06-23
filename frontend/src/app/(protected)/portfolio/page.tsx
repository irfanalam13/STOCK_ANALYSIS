"use client";

import { useState } from "react";

import {
  AllocationCard,
  PerformanceCard,
} from "@/components/portfolio/Analytics";
import { HoldingsTable } from "@/components/portfolio/HoldingsTable";
import { RiskPanel } from "@/components/portfolio/RiskPanel";
import { SummaryCards } from "@/components/portfolio/SummaryCards";
import { TradeModal } from "@/components/portfolio/TradeModal";
import { TransactionsTable } from "@/components/portfolio/TransactionsTable";
import { Button, Card, CardHeader, LoaderOverlay } from "@/components/ui";
import {
  usePortfolioAnalytics,
  usePortfolioSummary,
  usePortfolioTransactions,
} from "@/hooks/usePortfolio";

export default function PortfolioPage() {
  const { data: summary, isLoading } = usePortfolioSummary();
  const { data: analytics } = usePortfolioAnalytics();
  const { data: transactions = [] } = usePortfolioTransactions({ limit: 50 });

  const [tradeOpen, setTradeOpen] = useState(false);
  const [sellSymbol, setSellSymbol] = useState<string>("");

  const openBuy = () => {
    setSellSymbol("");
    setTradeOpen(true);
  };
  const openSell = (symbol: string) => {
    setSellSymbol(symbol);
    setTradeOpen(true);
  };

  if (isLoading || !summary) return <LoaderOverlay label="Loading portfolio…" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-fg">Portfolio</h1>
          <p className="text-sm text-muted">Paper trading · {summary.name}</p>
        </div>
        <Button onClick={openBuy}>+ Trade</Button>
      </div>

      <SummaryCards s={summary} />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card>
            <CardHeader title="Holdings" subtitle={`${summary.holdings.length} positions`} />
            <HoldingsTable holdings={summary.holdings} onSell={openSell} />
          </Card>
          <Card>
            <CardHeader title="Transaction History" />
            <TransactionsTable rows={transactions} />
          </Card>
        </div>

        <div className="space-y-6">
          <RiskPanel />
          {analytics && (
            <>
              <PerformanceCard a={analytics} />
              <AllocationCard a={analytics} />
            </>
          )}
        </div>
      </div>

      <TradeModal
        open={tradeOpen}
        onClose={() => setTradeOpen(false)}
        presetSymbol={sellSymbol}
        presetSide={sellSymbol ? "SELL" : "BUY"}
      />
    </div>
  );
}
