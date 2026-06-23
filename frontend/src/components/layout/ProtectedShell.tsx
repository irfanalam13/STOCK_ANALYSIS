"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { LoaderOverlay } from "@/components/ui";
import { MarketTicker } from "@/components/market/MarketTicker";
import { useMarketSocket } from "@/hooks/useWebSocket";
import { useLiveSnapshot } from "@/hooks/useStocks";
import { useMarketStore } from "@/store/market.store";
import { useAuthStore } from "@/store/auth.store";
import { ROUTES } from "@/utils/constants";
import { CACHE_KEYS, cacheSet } from "@/utils/offlineCache";
import { BottomNav } from "./BottomNav";
import { OfflineBanner } from "./OfflineBanner";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

/**
 * Auth gate + app chrome for every protected page. Also seeds the market store
 * with the initial Redis snapshot and opens the single live WebSocket.
 */
export function ProtectedShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const status = useAuthStore((s) => s.status);
  const authed = status === "authenticated";

  // Live data layer — one socket for the whole app.
  useMarketSocket(authed);
  const applyPrices = useMarketStore((s) => s.applyPrices);
  const { data: snapshot } = useLiveSnapshot();
  useEffect(() => {
    // Seed from the REST snapshot (seq=0 → always applied, never advances seq).
    if (snapshot?.quotes?.length) {
      applyPrices(0, snapshot.quotes);
      cacheSet(CACHE_KEYS.snapshot, snapshot.quotes); // offline fallback
    }
  }, [snapshot, applyPrices]);

  useEffect(() => {
    if (status === "unauthenticated") router.replace(ROUTES.login);
  }, [status, router]);

  if (!authed) {
    return (
      <div className="flex h-screen items-center justify-center">
        <LoaderOverlay label="Checking session…" />
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <MarketTicker />
        <OfflineBanner />
        {/* pb-20 on mobile keeps content clear of the bottom nav. */}
        <main className="flex-1 overflow-y-auto p-4 pb-20 md:pb-6 lg:p-6">
          {children}
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
