import { Card, CardHeader } from "@/components/ui";
import type { MarketDataPoint, Stock } from "@/types";
import { formatCurrency, formatVolume } from "@/utils/format";

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 py-2 last:border-0">
      <span className="text-sm text-muted">{label}</span>
      <span className="text-sm font-medium text-fg">{value}</span>
    </div>
  );
}

export function CompanyInfo({
  stock,
  latest,
}: {
  stock: Stock;
  latest?: MarketDataPoint;
}) {
  return (
    <Card>
      <CardHeader title="Company Info" />
      <Row label="Symbol" value={stock.symbol} />
      <Row label="Company" value={stock.company_name} />
      <Row label="Sector" value={stock.sector ?? "—"} />
      {latest && (
        <>
          <Row label="Open" value={formatCurrency(latest.open_price)} />
          <Row label="High" value={formatCurrency(latest.high_price)} />
          <Row label="Low" value={formatCurrency(latest.low_price)} />
          <Row label="Volume" value={formatVolume(latest.volume)} />
        </>
      )}
    </Card>
  );
}
