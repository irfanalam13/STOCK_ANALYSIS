"use client";

import Link from "next/link";

import { Card, CardHeader } from "@/components/ui";
import type { Mover } from "@/types";
import { ROUTES } from "@/utils/constants";
import { formatCurrency, formatPercent, formatVolume } from "@/utils/format";

export function MoversTable({
  title,
  rows,
  variant,
}: {
  title: string;
  rows: Mover[];
  variant: "gainers" | "losers";
}) {
  const tone = variant === "gainers" ? "text-up" : "text-down";
  return (
    <Card>
      <CardHeader title={title} subtitle={`${rows.length} symbols`} />
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-muted">
              <th className="py-2">Symbol</th>
              <th className="py-2 text-right">Price</th>
              <th className="py-2 text-right">Change</th>
              <th className="py-2 text-right">Volume</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.symbol} className="border-t border-border hover:bg-surface-2">
                <td className="py-2 font-medium">
                  <Link href={ROUTES.stock(r.symbol)} className="text-brand hover:underline">
                    {r.symbol}
                  </Link>
                </td>
                <td className="py-2 text-right tabular-nums">{formatCurrency(r.price)}</td>
                <td className={`py-2 text-right font-semibold tabular-nums ${tone}`}>
                  {formatPercent(r.change_percent)}
                </td>
                <td className="py-2 text-right tabular-nums text-muted">
                  {formatVolume(r.volume)}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={4} className="py-6 text-center text-muted">
                  No data — waiting for live market feed.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
