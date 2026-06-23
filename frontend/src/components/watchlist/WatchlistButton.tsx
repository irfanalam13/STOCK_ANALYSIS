"use client";

import { Button } from "@/components/ui";
import { useWatchlist } from "@/hooks/useWatchlist";
import { cn } from "@/utils/helpers";

export function WatchlistButton({
  symbol,
  variant = "secondary",
}: {
  symbol: string;
  variant?: "secondary" | "ghost";
}) {
  const { has, toggle } = useWatchlist();
  const active = has(symbol);

  return (
    <Button
      variant={variant}
      size="sm"
      onClick={(e) => {
        e.stopPropagation();
        toggle(symbol);
      }}
      aria-pressed={active}
    >
      <span className={cn(active ? "text-yellow-400" : "text-muted")}>
        {active ? "★" : "☆"}
      </span>
      {active ? "Watching" : "Watchlist"}
    </Button>
  );
}
