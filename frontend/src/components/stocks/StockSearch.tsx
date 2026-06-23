"use client";

import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";

import { Input } from "@/components/ui";
import { useStocks } from "@/hooks/useStocks";
import { ROUTES } from "@/utils/constants";

/** Global debounced search with an instant results dropdown. */
export function StockSearch() {
  const router = useRouter();
  const { data: stocks } = useStocks();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const [debounced, setDebounced] = useState("");

  const onChange = (value: string) => {
    setQuery(value);
    setOpen(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebounced(value), 250);
  };

  const results = useMemo(() => {
    const q = debounced.trim().toLowerCase();
    if (!q || !stocks) return [];
    return stocks
      .filter(
        (s) =>
          s.symbol.toLowerCase().includes(q) ||
          s.company_name.toLowerCase().includes(q),
      )
      .slice(0, 8);
  }, [debounced, stocks]);

  const go = (symbol: string) => {
    setOpen(false);
    setQuery("");
    router.push(ROUTES.stock(symbol));
  };

  return (
    <div className="relative w-full max-w-md">
      <Input
        placeholder="Search symbol or company…"
        value={query}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && results.length > 0 && (
        <div className="absolute z-40 mt-1 w-full overflow-hidden rounded-lg border border-border bg-surface shadow-lg">
          {results.map((s) => (
            <button
              key={s.id}
              onMouseDown={() => go(s.symbol)}
              className="flex w-full items-center justify-between px-3 py-2 text-left text-sm hover:bg-surface-2"
            >
              <span className="font-semibold text-fg">{s.symbol}</span>
              <span className="truncate pl-3 text-xs text-muted">
                {s.company_name}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
