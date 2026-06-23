"use client";

import { Dropdown, DropdownItem } from "@/components/ui";
import { StockSearch } from "@/components/stocks/StockSearch";
import { useAuth } from "@/hooks/useAuth";
import { useMarketStore } from "@/store/market.store";
import { ThemeToggle } from "./theme";

export function Topbar() {
  const { user, signOut } = useAuth();
  const connected = useMarketStore((s) => s.connected);

  return (
    <header className="flex h-16 items-center gap-3 border-b border-border bg-surface px-4">
      <div className="flex-1">
        <StockSearch />
      </div>

      <span
        className="hidden items-center gap-1.5 text-xs text-muted sm:flex"
        title={connected ? "Live market feed connected" : "Reconnecting…"}
      >
        <span className={`h-2 w-2 rounded-full ${connected ? "bg-up animate-pulse" : "bg-muted"}`} />
        {connected ? "Live" : "Offline"}
      </span>

      <ThemeToggle />

      <Dropdown
        trigger={
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand/15 font-semibold text-brand">
            {(user?.email[0] ?? "U").toUpperCase()}
          </div>
        }
      >
        <div className="px-3 py-2 text-xs text-muted">
          <div className="font-medium text-fg">{user?.email}</div>
          <div className="capitalize">{user?.role}</div>
        </div>
        <DropdownItem onClick={signOut}>Sign out</DropdownItem>
      </Dropdown>
    </header>
  );
}
