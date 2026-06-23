import type {
  PortfolioAnalytics,
  PortfolioSummary,
  PortfolioTransaction,
  RiskSummary,
  TradeSide,
} from "@/types";
import { api } from "./axios";

export interface TransactionFilters {
  symbol?: string;
  side?: TradeSide;
  limit?: number;
}

export const portfolioApi = {
  async buy(symbol: string, quantity: number): Promise<PortfolioTransaction> {
    const { data } = await api.post("/portfolio/buy", { symbol, quantity });
    return data;
  },
  async sell(symbol: string, quantity: number): Promise<PortfolioTransaction> {
    const { data } = await api.post("/portfolio/sell", { symbol, quantity });
    return data;
  },
  async summary(): Promise<PortfolioSummary> {
    const { data } = await api.get("/portfolio/summary");
    return data;
  },
  async analytics(): Promise<PortfolioAnalytics> {
    const { data } = await api.get("/portfolio/analytics");
    return data;
  },
  async riskSummary(): Promise<RiskSummary> {
    const { data } = await api.get("/portfolio/risk-summary");
    return data;
  },
  async transactions(filters: TransactionFilters = {}): Promise<PortfolioTransaction[]> {
    const { data } = await api.get("/portfolio/transactions", { params: filters });
    return data;
  },
};
