"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/utils/helpers";

/**
 * Renders a price that briefly flashes green/red whenever its value changes —
 * the UI-level transition the spec asks for on every tick.
 */
export function AnimatedPrice({
  value,
  format,
  className,
}: {
  value: number | null | undefined;
  format: (v: number | null | undefined) => string;
  className?: string;
}) {
  const prev = useRef<number | null | undefined>(value);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);

  useEffect(() => {
    if (value == null || prev.current == null) {
      prev.current = value;
      return;
    }
    if (value > prev.current) setFlash("up");
    else if (value < prev.current) setFlash("down");
    prev.current = value;

    const t = setTimeout(() => setFlash(null), 600);
    return () => clearTimeout(t);
  }, [value]);

  return (
    <span
      className={cn(
        "tabular-nums transition-colors duration-500 rounded px-1",
        flash === "up" && "bg-up/25",
        flash === "down" && "bg-down/25",
        className,
      )}
    >
      {format(value)}
    </span>
  );
}
