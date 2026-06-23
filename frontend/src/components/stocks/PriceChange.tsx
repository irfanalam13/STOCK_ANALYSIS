import { Badge } from "@/components/ui";
import { formatPercent } from "@/utils/format";

/** Reusable up/down change indicator driven by a percentage value. */
export function PriceChange({
  pct,
  className,
}: {
  pct: number | null | undefined;
  className?: string;
}) {
  if (pct == null) return <span className="text-muted">—</span>;
  const tone = pct > 0 ? "up" : pct < 0 ? "down" : "neutral";
  const arrow = pct > 0 ? "▲" : pct < 0 ? "▼" : "•";
  return (
    <Badge tone={tone} className={className}>
      {arrow} {formatPercent(pct)}
    </Badge>
  );
}
