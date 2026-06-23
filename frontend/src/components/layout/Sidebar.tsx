"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ROUTES } from "@/utils/constants";
import { cn } from "@/utils/helpers";

const NAV = [
  { href: ROUTES.dashboard, label: "Dashboard", icon: "▦" },
  { href: ROUTES.stocks, label: "Stocks", icon: "📈" },
  { href: ROUTES.portfolio, label: "Portfolio", icon: "💼" },
  { href: ROUTES.watchlist, label: "Watchlist", icon: "★" },
  { href: ROUTES.profile, label: "Profile", icon: "👤" },
];

// Phase 7 — Advanced analytics dashboard.
const ANALYTICS_NAV = [
  { href: ROUTES.analyticsOverview, label: "Overview", icon: "📊" },
  { href: ROUTES.analyticsSectors, label: "Sectors", icon: "🏢" },
  { href: ROUTES.analyticsGainersLosers, label: "Gainers / Losers", icon: "🚀" },
  { href: ROUTES.analyticsHeatmap, label: "Heatmap", icon: "🔥" },
  { href: ROUTES.analyticsTechnical, label: "Technical", icon: "📉" },
  { href: ROUTES.analyticsAI, label: "AI Insights", icon: "🤖" },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-60 shrink-0 border-r border-border bg-surface md:flex md:flex-col">
      <div className="flex h-16 items-center gap-2 border-b border-border px-5">
        <span className="text-xl">📊</span>
        <span className="font-bold text-fg">NEPSE&nbsp;AI</span>
      </div>
      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {NAV.map((item) => {
          // Exact match for the dashboard root so analytics sub-routes don't
          // also light it up; prefix match for the rest.
          const active =
            item.href === ROUTES.dashboard
              ? pathname === item.href
              : pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-brand/15 text-brand"
                  : "text-muted hover:bg-surface-2 hover:text-fg",
              )}
            >
              <span className="w-5 text-center">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}

        <p className="px-3 pb-1 pt-4 text-xs font-semibold uppercase tracking-wide text-muted">
          Analytics
        </p>
        {ANALYTICS_NAV.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-brand/15 text-brand"
                  : "text-muted hover:bg-surface-2 hover:text-fg",
              )}
            >
              <span className="w-5 text-center">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-border p-4 text-xs text-muted">
        NEPSE Trading Platform
      </div>
    </aside>
  );
}
