import type { StockWithQuote } from "@/types";

export interface MarketStats {
  total: number;
  advancers: number;
  decliners: number;
  unchanged: number;
  totalVolume: number;
  avgChangePct: number;
  /** Synthetic NEPSE-style index: volume-weighted average price. */
  indexValue: number;
}

/** Derive headline market statistics from enriched stock rows. */
export function computeMarketStats(rows: StockWithQuote[]): MarketStats {
  const priced = rows.filter((r) => r.price != null);
  let advancers = 0;
  let decliners = 0;
  let unchanged = 0;
  let totalVolume = 0;
  let changeSum = 0;
  let weightedPrice = 0;
  let weightTotal = 0;

  for (const r of priced) {
    const pct = r.changePct ?? 0;
    if (pct > 0) advancers += 1;
    else if (pct < 0) decliners += 1;
    else unchanged += 1;
    totalVolume += r.volume ?? 0;
    changeSum += pct;
    const w = r.volume ?? 1;
    weightedPrice += (r.price ?? 0) * w;
    weightTotal += w;
  }

  return {
    total: priced.length,
    advancers,
    decliners,
    unchanged,
    totalVolume,
    avgChangePct: priced.length ? changeSum / priced.length : 0,
    indexValue: weightTotal ? weightedPrice / weightTotal : 0,
  };
}

export function topGainers(rows: StockWithQuote[], n = 5): StockWithQuote[] {
  return [...rows]
    .filter((r) => r.changePct != null)
    .sort((a, b) => (b.changePct ?? 0) - (a.changePct ?? 0))
    .slice(0, n);
}

export function topLosers(rows: StockWithQuote[], n = 5): StockWithQuote[] {
  return [...rows]
    .filter((r) => r.changePct != null)
    .sort((a, b) => (a.changePct ?? 0) - (b.changePct ?? 0))
    .slice(0, n);
}

export function topByVolume(rows: StockWithQuote[], n = 5): StockWithQuote[] {
  return [...rows]
    .filter((r) => r.volume != null)
    .sort((a, b) => (b.volume ?? 0) - (a.volume ?? 0))
    .slice(0, n);
}
