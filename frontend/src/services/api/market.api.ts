import type { LiveMarketResponse, MarketDataPoint } from "@/types";
import { api } from "./axios";

export const marketApi = {
  async live(): Promise<LiveMarketResponse> {
    const { data } = await api.get<LiveMarketResponse>("/market/live");
    return data;
  },
  async history(limit = 500): Promise<MarketDataPoint[]> {
    const { data } = await api.get<MarketDataPoint[]>("/market/history", {
      params: { limit },
    });
    return data;
  },
};
