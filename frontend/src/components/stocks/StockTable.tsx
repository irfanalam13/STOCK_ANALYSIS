"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Table, type Column } from "@/components/ui";
import { PriceChange } from "./PriceChange";
import type { StockWithQuote } from "@/types";
import { ROUTES } from "@/utils/constants";
import { formatCurrency, formatVolume } from "@/utils/format";

const PAGE_SIZE = 12;

export function StockTable({
  rows,
  query,
}: {
  rows: StockWithQuote[];
  query: string;
}) {
  const router = useRouter();
  const [sortKey, setSortKey] = useState<string>("symbol");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(0);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(
      (r) =>
        r.symbol.toLowerCase().includes(q) ||
        r.company_name.toLowerCase().includes(q),
    );
  }, [rows, query]);

  const sorted = useMemo(() => {
    const get = (r: StockWithQuote): number | string => {
      switch (sortKey) {
        case "price":
          return r.price ?? -Infinity;
        case "change":
          return r.changePct ?? -Infinity;
        case "volume":
          return r.volume ?? -Infinity;
        default:
          return r.symbol;
      }
    };
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filtered].sort((a, b) => {
      const av = get(a);
      const bv = get(b);
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * dir;
      return String(av).localeCompare(String(bv)) * dir;
    });
  }, [filtered, sortKey, sortDir]);

  const pageCount = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const paged = sorted.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  const onSort = (key: string) => {
    if (key === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("asc");
    }
    setPage(0);
  };

  const columns: Column<StockWithQuote>[] = [
    {
      key: "symbol",
      header: "Symbol",
      sortable: true,
      render: (r) => (
        <div>
          <div className="font-semibold text-fg">{r.symbol}</div>
          <div className="text-xs text-muted">{r.company_name}</div>
        </div>
      ),
    },
    {
      key: "price",
      header: "Price",
      align: "right",
      sortable: true,
      render: (r) => formatCurrency(r.price),
    },
    {
      key: "change",
      header: "Change %",
      align: "right",
      sortable: true,
      render: (r) => <PriceChange pct={r.changePct} />,
    },
    {
      key: "volume",
      header: "Volume",
      align: "right",
      sortable: true,
      render: (r) => formatVolume(r.volume),
    },
  ];

  return (
    <div className="space-y-3">
      <Table
        columns={columns}
        rows={paged}
        rowKey={(r) => r.id}
        sortKey={sortKey}
        sortDir={sortDir}
        onSort={onSort}
        onRowClick={(r) => router.push(ROUTES.stock(r.symbol))}
        emptyMessage="No stocks match your search."
      />
      <div className="flex items-center justify-between text-sm text-muted">
        <span>
          {sorted.length} result{sorted.length === 1 ? "" : "s"}
        </span>
        <div className="flex items-center gap-2">
          <button
            className="rounded-md border border-border px-2 py-1 disabled:opacity-40"
            disabled={safePage === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            Prev
          </button>
          <span>
            {safePage + 1} / {pageCount}
          </span>
          <button
            className="rounded-md border border-border px-2 py-1 disabled:opacity-40"
            disabled={safePage >= pageCount - 1}
            onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
