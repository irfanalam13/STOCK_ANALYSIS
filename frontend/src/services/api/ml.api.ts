// Client for the standalone ML service (Phase 4). Separate base URL from the
// core API, but reuses the same JWT — the ML service shares the SECRET_KEY.
import axios from "axios";

import type { AISignal, MarketDataPoint } from "@/types";
import { ML_API_URL } from "@/utils/constants";
import { tokenStore } from "./tokenStore";

const ml = axios.create({
  baseURL: ML_API_URL,
  headers: { "Content-Type": "application/json" },
});

ml.interceptors.request.use((config) => {
  const token = tokenStore.getAccess();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

function toFeatures(bar?: MarketDataPoint) {
  if (!bar) return undefined;
  return {
    open: bar.open_price,
    high: bar.high_price,
    low: bar.low_price,
    close: bar.close_price,
    volume: bar.volume,
  };
}

export const mlApi = {
  async signal(symbol: string, latest?: MarketDataPoint): Promise<AISignal> {
    const { data } = await ml.post<AISignal>("/signal/stock", {
      symbol,
      features: toFeatures(latest),
    });
    return data;
  },
};
