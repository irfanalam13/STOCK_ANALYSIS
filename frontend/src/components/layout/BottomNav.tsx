"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ROUTES } from "@/utils/constants";
import { cn } from "@/utils/helpers";

// Mobile-only bottom navigation bar (hidden on md+ where the sidebar shows).
const ITEMS = [
  { href: ROUTES.dashboard, label: "Home", icon: "▦" },
  { href: ROUTES.stocks, label: "Stocks", icon: "📈" },
  { href: ROUTES.watchlist, label: "Watch", icon: "★" },
  { href: ROUTES.analyticsOverview, label: "Analytics", icon: "📊" },
  { href: ROUTES.portfolio, label: "Portfolio", icon: "💼" },
];

export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav className="fixed inset-x-0 bottom-0 z-30 flex border-t border-border bg-surface md:hidden">
      {ITEMS.map((item) => {
        const active =
          pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] font-medium transition-colors",
              active ? "text-brand" : "text-muted",
            )}
          >
            <span className="text-lg leading-none">{item.icon}</span>
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
