import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

import type { LiveQuote, Stock, StockWithQuote } from "@/types";

/** Tailwind-aware className combiner used by every UI component. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Trailing-edge debounce for search inputs and other rapid events. */
export function debounce<A extends unknown[]>(
  fn: (...args: A) => void,
  delay = 300,
): (...args: A) => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  return (...args: A) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

/** Merge the stock catalog with a symbol→quote map into table-ready rows. */
export function enrichStocks(
  stocks: Stock[],
  quotes: Record<string, LiveQuote>,
): StockWithQuote[] {
  return stocks.map((s) => {
    const q = quotes[s.symbol];
    if (!q) {
      return {
        ...s,
        price: null,
        open: null,
        changeAbs: null,
        changePct: null,
        volume: null,
      };
    }
    return {
      ...s,
      price: q.price,
      open: q.price - q.change,
      changeAbs: q.change,
      changePct: q.change_percent,
      volume: q.volume,
    };
  });
}
