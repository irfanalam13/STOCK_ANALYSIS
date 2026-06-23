import type { ReactNode } from "react";

import { cn } from "@/utils/helpers";

type Tone = "neutral" | "up" | "down" | "brand";

const tones: Record<Tone, string> = {
  neutral: "bg-surface-2 text-muted",
  up: "bg-up/15 text-up",
  down: "bg-down/15 text-down",
  brand: "bg-brand/15 text-brand",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
