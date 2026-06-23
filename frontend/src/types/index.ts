// Shared domain types. These mirror the Phase 1 FastAPI response schemas.

export type UserRole = "admin" | "trader" | "viewer";

export interface User {
  id: number;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface Stock {
  id: number;
  symbol: string;
  company_name: string;
  sector: string | null;
}

/** A single OHLCV point as stored in PostgreSQL (history endpoints). */
export interface MarketDataPoint {
  id: number;
  stock_id: number;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
  timestamp: string;
}

/** Real-time price tick (matches the backend PriceUpdate / snapshot payload). */
export interface LiveQuote {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  timestamp: string;
}

/** Real-time OHLC candle update (for incremental chart patching). */
export interface Candle {
  symbol: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  interval: string;
  timestamp: string;
}

export interface VolumeUpdate {
  symbol: string;
  volume: number;
  timestamp: string;
}

export interface LiveMarketResponse {
  quotes: LiveQuote[];
  source: string;
  stale: boolean;
}

/** Stock row enriched with its latest quote — used by tables/cards. */
export interface StockWithQuote extends Stock {
  price: number | null;
  open: number | null;
  changeAbs: number | null;
  changePct: number | null;
  volume: number | null;
}

// ---- Portfolio (paper trading) ----
export type TradeSide = "BUY" | "SELL";

export interface HoldingRisk {
  volatility_score: number;
  trend_signal: "BUY" | "SELL" | "HOLD";
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  confidence: number;
}

export interface Holding {
  symbol: string;
  company_name: string;
  sector: string | null;
  quantity: number;
  avg_buy_price: number;
  current_price: number;
  market_value: number;
  cost_basis: number;
  unrealized_pnl: number;
  unrealized_pct: number;
  realized_pnl: number;
  risk: HoldingRisk | null;
}

export interface RiskSummary {
  portfolio_id: number;
  portfolio_risk_score: number;
  high_risk_holdings: string[];
  warnings: string[];
}

export interface PortfolioSummary {
  portfolio_id: number;
  name: string;
  initial_balance: number;
  cash_balance: number;
  holdings_value: number;
  total_value: number;
  total_unrealized_pnl: number;
  total_realized_pnl: number;
  total_pnl: number;
  roi: number;
  holdings: Holding[];
}

export interface PortfolioTransaction {
  id: number;
  symbol: string;
  side: TradeSide;
  quantity: number;
  price: number;
  fee: number;
  total_value: number;
  realized_pnl: number | null;
  timestamp: string;
}

export interface AllocationSlice {
  label: string;
  value: number;
  pct: number;
}

export interface PortfolioAnalytics {
  portfolio_id: number;
  roi: number;
  total_value: number;
  invested: number;
  total_pnl: number;
  total_trades: number;
  win_trades: number;
  loss_trades: number;
  win_loss_ratio: number;
  allocation: AllocationSlice[];
  risk: {
    score: number;
    concentration: number;
    sectors: number;
    exposure: number;
  };
}

/** Fused AI trading signal from the ML service (`POST /signal/stock`). */
export interface AISignal {
  symbol: string;
  signal: "BUY" | "SELL" | "HOLD";
  strength: "STRONG" | "MODERATE" | "WEAK" | "NEUTRAL";
  confidence: number;
  reason: string[];
  details: {
    predicted_price: number;
    predicted_return: number;
    trend: "UPTREND" | "DOWNTREND" | "SIDEWAYS";
    volatility: "LOW" | "MEDIUM" | "HIGH";
    score: number;
    fallback: boolean;
  };
}

// ---- Analytics dashboard (Phase 7) ----
export interface MarketOverview {
  index_value: number;
  index_change_percent: number;
  total_stocks: number;
  advancers: number;
  decliners: number;
  unchanged: number;
  total_volume: number;
  total_turnover: number;
  avg_change_percent: number;
  sentiment: "Bullish" | "Bearish" | "Neutral";
  sentiment_score: number;
}

export interface SectorPerformance {
  sector: string;
  stocks: number;
  avg_change_percent: number;
  advancers: number;
  decliners: number;
  total_volume: number;
  total_turnover: number;
  relative_strength: number;
}

export interface Mover {
  symbol: string;
  price: number;
  change: number;
  change_percent: number;
  volume: number;
  turnover: number;
}

export interface HeatmapTile {
  symbol: string;
  sector: string;
  change_percent: number;
  price: number;
  volume: number;
  turnover: number;
  weight: number;
}

export interface IndicatorPoint {
  timestamp: string;
  value: number | null;
}

export interface Suggestion {
  action: "BUY" | "SELL" | "HOLD";
  confidence: number;
  rationale: string;
}

export interface TechnicalSignal {
  indicator: string;
  signal: "BUY" | "SELL" | "HOLD";
  note: string;
}

export interface TechnicalResponse {
  symbol: string;
  timeframe: string;
  points: number;
  latest: {
    price: number | null;
    rsi: number | null;
    macd: number | null;
    macd_signal: number | null;
    macd_histogram: number | null;
    sma_20: number | null;
    sma_50: number | null;
    ema_12: number | null;
    ema_26: number | null;
    bollinger_upper: number | null;
    bollinger_lower: number | null;
    signals: TechnicalSignal[];
  };
  series: Record<string, IndicatorPoint[]>;
  insights: string[];
  suggestion: Suggestion;
}

export interface AIInsightResponse {
  scope: string;
  insights: string[];
  suggestion: Suggestion | null;
}

export type Timeframe = "1D" | "1W" | "1M";

/** Discriminated union of every server -> client WebSocket frame. */
export type WsServerMessage =
  | { type: "connected"; client_id: string }
  | { type: "subscribed"; symbols: string[]; ticker?: boolean }
  | { type: "prices"; seq: number; data: LiveQuote[] }
  | { type: "ohlc"; seq: number; data: Candle[] }
  | { type: "volume"; seq: number; data: VolumeUpdate[] }
  | { type: "pong" }
  | { type: "heartbeat"; ts: string };
