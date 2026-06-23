"use client";

import { Card, CardHeader, Spinner } from "@/components/ui";
import {
  useNotificationPreferences,
  useUpdatePreferences,
} from "@/hooks/useMobile";
import type { NotificationPreferences } from "@/services/api/mobile.api";
import { cn } from "@/utils/helpers";

const FIELDS: { key: keyof NotificationPreferences; label: string; hint: string }[] = [
  { key: "push_enabled", label: "Push notifications", hint: "Mobile & browser push" },
  { key: "email_enabled", label: "Email", hint: "Alert emails" },
  { key: "sms_enabled", label: "SMS", hint: "Text-message fallback" },
  { key: "price_alerts", label: "Price alerts", hint: "Threshold & % moves" },
  { key: "portfolio_alerts", label: "Portfolio alerts", hint: "P/L updates" },
  { key: "news_alerts", label: "Market news", hint: "News notifications" },
];

function Toggle({ on, onClick }: { on: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={onClick}
      className={cn(
        "relative h-6 w-11 rounded-full transition-colors",
        on ? "bg-brand" : "bg-surface-2",
      )}
    >
      <span
        className={cn(
          "absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform",
          on ? "translate-x-5" : "translate-x-0.5",
        )}
      />
    </button>
  );
}

export function NotificationSettings() {
  const { data, isLoading } = useNotificationPreferences();
  const update = useUpdatePreferences();

  if (isLoading || !data) {
    return (
      <Card>
        <CardHeader title="Notification Preferences" />
        <Spinner />
      </Card>
    );
  }

  const toggle = (key: keyof NotificationPreferences) =>
    update.mutate({ ...data, [key]: !data[key] });

  return (
    <Card>
      <CardHeader title="Notification Preferences" subtitle="Choose how we reach you" />
      <div className="space-y-1">
        {FIELDS.map((f) => (
          <div
            key={f.key}
            className="flex items-center justify-between border-b border-border/60 py-2.5 last:border-0"
          >
            <div>
              <p className="text-sm font-medium text-fg">{f.label}</p>
              <p className="text-xs text-muted">{f.hint}</p>
            </div>
            <Toggle on={data[f.key]} onClick={() => toggle(f.key)} />
          </div>
        ))}
      </div>
    </Card>
  );
}
