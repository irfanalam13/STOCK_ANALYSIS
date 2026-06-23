import type { MarketDataPoint, Stock } from "@/types";
import { api } from "./axios";

export const stocksApi = {
  async list(): Promise<Stock[]> {
    const { data } = await api.get<Stock[]>("/stocks");
    return data;
  },
  async get(symbol: string): Promise<Stock> {
    const { data } = await api.get<Stock>(`/stocks/${symbol}`);
    return data;
  },
  async history(symbol: string, limit = 200): Promise<MarketDataPoint[]> {
    const { data } = await api.get<MarketDataPoint[]>(
      `/stocks/${symbol}/history`,
      { params: { limit } },
    );
    return data;
  },
};
