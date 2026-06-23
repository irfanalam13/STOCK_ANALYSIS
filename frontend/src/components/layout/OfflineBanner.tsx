"use client";

import { useOnlineStatus } from "@/hooks/useOnlineStatus";

/** Sticky notice shown when the device loses connectivity. */
export function OfflineBanner() {
  const online = useOnlineStatus();
  if (online) return null;
  return (
    <div className="bg-down/15 px-4 py-1.5 text-center text-xs font-medium text-down">
      You&apos;re offline — showing cached data. We&apos;ll sync when you&apos;re back.
    </div>
  );
}
