import { api } from "./axios";

export interface MobileHome {
  overview: Record<string, number | string>;
  watchlist: Array<Record<string, unknown>>;
  portfolio: Record<string, unknown>;
  preferences: NotificationPreferences;
}

export interface NotificationPreferences {
  push_enabled: boolean;
  email_enabled: boolean;
  sms_enabled: boolean;
  price_alerts: boolean;
  portfolio_alerts: boolean;
  news_alerts: boolean;
}

export interface WatchlistSyncItem {
  symbol: string;
  updated_at: number;
  deleted: boolean;
}

export interface WatchlistSyncResponse {
  items: WatchlistSyncItem[];
  symbols: string[];
}

export const mobileApi = {
  async home(): Promise<MobileHome> {
    const { data } = await api.get<MobileHome>("/mobile/home");
    return data;
  },
  async getWatchlist(): Promise<string[]> {
    const { data } = await api.get<string[]>("/mobile/watchlist");
    return data;
  },
  async syncWatchlist(items: WatchlistSyncItem[]): Promise<WatchlistSyncResponse> {
    const { data } = await api.post<WatchlistSyncResponse>("/mobile/watchlist/sync", {
      items,
    });
    return data;
  },
  async registerDevice(token: string, platform = "web"): Promise<void> {
    await api.post("/mobile/devices", { token, platform });
  },
  async getPreferences(): Promise<NotificationPreferences> {
    const { data } = await api.get<NotificationPreferences>("/mobile/preferences");
    return data;
  },
  async updatePreferences(
    prefs: NotificationPreferences,
  ): Promise<NotificationPreferences> {
    const { data } = await api.put<NotificationPreferences>("/mobile/preferences", prefs);
    return data;
  },
};
