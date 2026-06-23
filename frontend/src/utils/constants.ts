export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/market";

export const ML_API_URL =
  process.env.NEXT_PUBLIC_ML_API_URL ?? "http://localhost:8100";

// Simulated broker commission (matches backend PORTFOLIO_FEE_RATE) — display only.
export const PORTFOLIO_FEE_RATE = 0.004;

export const STORAGE_KEYS = {
  accessToken: "nepse.accessToken",
  refreshToken: "nepse.refreshToken",
  theme: "nepse.theme",
  watchlist: "nepse.watchlist",
} as const;

export const ROUTES = {
  login: "/auth/login",
  signup: "/auth/signup",
  dashboard: "/dashboard",
  stocks: "/stocks",
  stock: (symbol: string) => `/stocks/${symbol}`,
  watchlist: "/watchlist",
  portfolio: "/portfolio",
  profile: "/profile",
  // Phase 7 — Advanced analytics dashboard
  analyticsOverview: "/dashboard/overview",
  analyticsSectors: "/dashboard/sectors",
  analyticsGainersLosers: "/dashboard/gainers-losers",
  analyticsHeatmap: "/dashboard/heatmap",
  analyticsTechnical: "/dashboard/technical",
  analyticsAI: "/dashboard/ai-insights",
} as const;

// Centralized React Query keys to keep cache invalidation consistent.
export const QUERY_KEYS = {
  me: ["me"] as const,
  stocks: ["stocks"] as const,
  stock: (symbol: string) => ["stock", symbol] as const,
  history: (symbol: string) => ["history", symbol] as const,
  live: ["market", "live"] as const,
  aiSignal: (symbol: string) => ["ai", "signal", symbol] as const,
  portfolioSummary: ["portfolio", "summary"] as const,
  portfolioAnalytics: ["portfolio", "analytics"] as const,
  portfolioTransactions: ["portfolio", "transactions"] as const,
  portfolioRisk: ["portfolio", "risk-summary"] as const,
  // Phase 7 analytics
  analyticsOverview: ["analytics", "overview"] as const,
  analyticsSectors: ["analytics", "sectors"] as const,
  analyticsMovers: (dir: string, top: number, minVol: number) =>
    ["analytics", "movers", dir, top, minVol] as const,
  analyticsHeatmap: (mode: string, sector: string | null) =>
    ["analytics", "heatmap", mode, sector ?? "all"] as const,
  analyticsTechnical: (symbol: string, tf: string) =>
    ["analytics", "technical", symbol, tf] as const,
  analyticsAI: (scope: string) => ["analytics", "ai", scope] as const,
};
