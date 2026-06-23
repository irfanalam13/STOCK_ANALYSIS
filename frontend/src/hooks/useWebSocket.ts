"use client";

import { useEffect, useRef } from "react";

import { tokenStore } from "@/services/api/tokenStore";
import { useMarketStore } from "@/store/market.store";
import type { WsServerMessage } from "@/types";
import { WS_URL } from "@/utils/constants";

const PING_INTERVAL = 15_000; // client heartbeat to keep the connection alive
const MAX_BACKOFF = 10_000;

/**
 * Maintains a single live WebSocket to `/ws/market`:
 *
 * - Subscribes to the `ticker` firehose so every store-backed component (ticker
 *   bar, tables, watchlist, charts) gets updates from one connection. The
 *   protocol also supports per-symbol `subscribe`/`unsubscribe` for fine-grained
 *   scaling; the bounded NEPSE symbol set makes the firehose the simpler choice.
 * - Applies price/OHLC batches into the market store (seq-deduped there).
 * - Sends application-level pings; auto-reconnects with exponential backoff.
 *
 * Mount exactly once, high in the protected tree (see ProtectedShell).
 */
export function useMarketSocket(enabled: boolean): void {
  const applyPrices = useMarketStore((s) => s.applyPrices);
  const applyCandles = useMarketStore((s) => s.applyCandles);
  const setConnected = useMarketStore((s) => s.setConnected);

  const socketRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const closedRef = useRef(false);

  useEffect(() => {
    if (!enabled) return;
    closedRef.current = false;
    let reconnectTimer: ReturnType<typeof setTimeout>;
    let pingTimer: ReturnType<typeof setInterval>;

    const connect = () => {
      const token = tokenStore.getAccess();
      if (!token) return;

      const ws = new WebSocket(`${WS_URL}?token=${encodeURIComponent(token)}`);
      socketRef.current = ws;

      ws.onopen = () => {
        retryRef.current = 0;
        setConnected(true);
        // Subscribe to the global firehose for the ticker + lists + charts.
        ws.send(JSON.stringify({ action: "subscribe", channel: "ticker" }));
        pingTimer = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: "ping" }));
          }
        }, PING_INTERVAL);
      };

      ws.onmessage = (event) => {
        let msg: WsServerMessage;
        try {
          msg = JSON.parse(event.data) as WsServerMessage;
        } catch {
          return; // ignore malformed frames
        }
        switch (msg.type) {
          case "prices":
            applyPrices(msg.seq, msg.data);
            break;
          case "ohlc":
            applyCandles(msg.seq, msg.data);
            break;
          // pong / heartbeat / connected / subscribed: liveness only.
        }
      };

      ws.onclose = () => {
        setConnected(false);
        clearInterval(pingTimer);
        if (closedRef.current) return;
        const delay = Math.min(1000 * 2 ** retryRef.current, MAX_BACKOFF);
        retryRef.current += 1;
        reconnectTimer = setTimeout(connect, delay);
      };

      ws.onerror = () => ws.close();
    };

    connect();

    return () => {
      closedRef.current = true;
      clearTimeout(reconnectTimer);
      clearInterval(pingTimer);
      socketRef.current?.close();
      setConnected(false);
    };
  }, [enabled, applyPrices, applyCandles, setConnected]);
}
