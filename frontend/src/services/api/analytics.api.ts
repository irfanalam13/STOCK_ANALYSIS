import type {
  AIInsightResponse,
  HeatmapTile,
  MarketOverview,
  Mover,
  SectorPerformance,
  TechnicalResponse,
} from "@/types";
import { api } from "./axios";

export const analyticsApi = {
  async overview(): Promise<MarketOverview> {
    const { data } = await api.get<MarketOverview>("/analytics/overview");
    return data;
  },
  async sectors(): Promise<SectorPerformance[]> {
    const { data } = await api.get<SectorPerformance[]>("/analytics/sectors");
    return data;
  },
  async movers(
    direction: "gainers" | "losers",
    top = 10,
    minVolume = 0,
  ): Promise<Mover[]> {
    const { data } = await api.get<Mover[]>(`/analytics/${direction}`, {
      params: { top, min_volume: minVolume },
    });
    return data;
  },
  async heatmap(
    mode: "change" | "volume" = "change",
    sector?: string | null,
  ): Promise<HeatmapTile[]> {
    const { data } = await api.get<HeatmapTile[]>("/analytics/heatmap", {
      params: { mode, ...(sector ? { sector } : {}) },
    });
    return data;
  },
  async technical(symbol: string, timeframe = "1M"): Promise<TechnicalResponse> {
    const { data } = await api.get<TechnicalResponse>(
      `/analytics/technical/${symbol}`,
      { params: { timeframe } },
    );
    return data;
  },
  async marketInsights(): Promise<AIInsightResponse> {
    const { data } = await api.get<AIInsightResponse>("/analytics/ai-insights");
    return data;
  },
  async symbolInsights(symbol: string, timeframe = "1M"): Promise<AIInsightResponse> {
    const { data } = await api.get<AIInsightResponse>(
      `/analytics/ai-insights/${symbol}`,
      { params: { timeframe } },
    );
    return data;
  },
};
