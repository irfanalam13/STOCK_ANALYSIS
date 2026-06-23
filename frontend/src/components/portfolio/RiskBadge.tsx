import { Badge } from "@/components/ui";
import type { HoldingRisk } from "@/types";

const RISK_TONE = {
  LOW: { tone: "up" as const, dot: "🟢" },
  MEDIUM: { tone: "neutral" as const, dot: "🟡" },
  HIGH: { tone: "down" as const, dot: "🔴" },
};

/** Per-holding risk badge driven by the ML risk level. */
export function RiskBadge({ risk }: { risk: HoldingRisk | null }) {
  if (!risk) return <span className="text-xs text-muted">—</span>;
  const { tone, dot } = RISK_TONE[risk.risk_level];
  return (
    <Badge tone={tone}>
      {dot} {risk.risk_level}
    </Badge>
  );
}
