"use client";

import { AxiosError } from "axios";
import { useEffect, useState } from "react";

import { Button, Input, Modal } from "@/components/ui";
import { useAISignal } from "@/hooks/useAI";
import { useTrade } from "@/hooks/usePortfolio";
import { useMarketStore } from "@/store/market.store";
import type { TradeSide } from "@/types";
import { PORTFOLIO_FEE_RATE } from "@/utils/constants";
import { formatCurrency, formatPercent } from "@/utils/format";
import { cn } from "@/utils/helpers";

interface TradeModalProps {
  open: boolean;
  onClose: () => void;
  presetSymbol?: string;
  presetSide?: TradeSide;
}

export function TradeModal({ open, onClose, presetSymbol = "", presetSide = "BUY" }: TradeModalProps) {
  const [symbol, setSymbol] = useState(presetSymbol);
  const [side, setSide] = useState<TradeSide>(presetSide);
  const [quantity, setQuantity] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const trade = useTrade();

  // Live price for the chosen symbol (for cost estimation).
  const cleanSymbol = symbol.trim().toUpperCase();
  const livePrice = useMarketStore((s) => s.quotes[cleanSymbol]?.price);
  // AI risk/signal check before executing (only for a settled symbol).
  const { data: ai } = useAISignal(cleanSymbol.length >= 3 ? cleanSymbol : "");

  useEffect(() => {
    if (open) {
      setSymbol(presetSymbol);
      setSide(presetSide);
      setQuantity(1);
      setError(null);
      trade.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, presetSymbol, presetSide]);

  const gross = livePrice ? livePrice * quantity : null;
  const fee = gross != null ? gross * PORTFOLIO_FEE_RATE : null;
  const estimate =
    gross != null && fee != null
      ? side === "BUY"
        ? gross + fee
        : gross - fee
      : null;

  const submit = async () => {
    setError(null);
    const sym = symbol.trim().toUpperCase();
    if (!sym || quantity < 1) {
      setError("Enter a symbol and a quantity ≥ 1");
      return;
    }
    try {
      await trade.mutateAsync({ side, symbol: sym, quantity });
      onClose();
    } catch (err) {
      setError(
        err instanceof AxiosError
          ? String(err.response?.data?.detail ?? "Trade failed")
          : "Trade failed",
      );
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Trade">
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-2">
          {(["BUY", "SELL"] as TradeSide[]).map((s) => (
            <button
              key={s}
              onClick={() => setSide(s)}
              className={cn(
                "rounded-lg border py-2 font-semibold transition-colors",
                side === s && s === "BUY" && "border-up bg-up/15 text-up",
                side === s && s === "SELL" && "border-down bg-down/15 text-down",
                side !== s && "border-border text-muted hover:bg-surface-2",
              )}
            >
              {s}
            </button>
          ))}
        </div>

        <Input
          label="Symbol"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="e.g. NABIL"
          disabled={Boolean(presetSymbol)}
        />
        <Input
          label="Quantity"
          type="number"
          min={1}
          value={quantity}
          onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
        />

        {ai && (
          <div
            className={cn(
              "rounded-lg border px-3 py-2 text-sm",
              ai.details.volatility === "HIGH" || ai.signal === "SELL"
                ? "border-down/40 bg-down/10 text-down"
                : "border-border bg-surface-2 text-fg",
            )}
          >
            <div className="flex items-center justify-between font-medium">
              <span>
                AI signal: {ai.signal}{" "}
                <span className="text-xs opacity-80">({Math.round(ai.confidence * 100)}%)</span>
              </span>
              <span className="text-xs">Volatility: {ai.details.volatility}</span>
            </div>
            {(ai.details.volatility === "HIGH" || ai.signal === "SELL") && (
              <p className="mt-1 text-xs">
                ⚠️ Elevated risk — predicted move {formatPercent(ai.details.predicted_return * 100)}.
                Consider your exposure before confirming.
              </p>
            )}
          </div>
        )}

        <div className="rounded-lg bg-surface-2 p-3 text-sm">
          <Row label="Market price" value={livePrice ? formatCurrency(livePrice) : "live at execution"} />
          <Row label={`Fee (${(PORTFOLIO_FEE_RATE * 100).toFixed(1)}%)`} value={fee != null ? formatCurrency(fee) : "—"} />
          <Row
            label={side === "BUY" ? "Est. cost" : "Est. proceeds"}
            value={estimate != null ? formatCurrency(estimate) : "—"}
            bold
          />
        </div>

        {error && <p className="text-sm text-down">{error}</p>}

        <div className="flex gap-2">
          <Button variant="secondary" className="flex-1" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant={side === "SELL" ? "danger" : "primary"}
            className="flex-1"
            loading={trade.isPending}
            onClick={submit}
          >
            Confirm {side}
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className="flex justify-between py-1">
      <span className="text-muted">{label}</span>
      <span className={cn("tabular-nums text-fg", bold && "font-semibold")}>{value}</span>
    </div>
  );
}
