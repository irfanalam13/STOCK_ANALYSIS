import { cn } from "@/utils/helpers";

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-block h-5 w-5 animate-spin rounded-full border-2 border-muted border-t-brand",
        className,
      )}
      role="status"
      aria-label="Loading"
    />
  );
}

export function LoaderOverlay({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex h-40 w-full flex-col items-center justify-center gap-3 text-muted">
      <Spinner className="h-7 w-7" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

/** Skeleton block for content-aware loading states. */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cn("animate-pulse rounded-md bg-surface-2", className)} />
  );
}
