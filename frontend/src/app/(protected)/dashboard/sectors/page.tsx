"use client";

import { SectorTable } from "@/components/analytics/SectorTable";
import { Skeleton } from "@/components/ui";
import { useSectors } from "@/hooks/useAnalytics";

export default function SectorsPage() {
  const { data, isLoading } = useSectors();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-fg">Sector Performance</h1>
        <p className="text-sm text-muted">
          Sector strength, breadth, and relative performance vs the market
        </p>
      </div>
      {isLoading ? <Skeleton className="h-64 w-full" /> : <SectorTable rows={data ?? []} />}
    </div>
  );
}
