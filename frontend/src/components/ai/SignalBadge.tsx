import type { AISignal } from "@/types";
import { cn } from "@/utils/helpers";

const SIGNAL_STYLES: Record<AISignal["signal"], string> = {
  BUY: "bg-up/15 text-up border-up/30",
  SELL: "bg-down/15 text-down border-down/30",
  HOLD: "bg-surface-2 text-muted border-border",
};

export function SignalBadge({
  signal,
  strength,
}: {
  signal: AISignal["signal"];
  strength: AISignal["strength"];
}) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 font-bold",
        SIGNAL_STYLES[signal],
      )}
    >
      <span className="text-lg">{signal}</span>
      <span className="text-xs font-medium opacity-80">{strength}</span>
    </div>
  );
}
