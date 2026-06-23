"use client";

import { ConfidenceMeter } from "@/components/ai/ConfidenceMeter";
import { Card, CardHeader } from "@/components/ui";
import type { Suggestion } from "@/types";
import { cn } from "@/utils/helpers";

const ACTION_STYLES: Record<Suggestion["action"], string> = {
  BUY: "bg-up/15 text-up border-up/30",
  SELL: "bg-down/15 text-down border-down/30",
  HOLD: "bg-surface-2 text-muted border-border",
};

export function InsightList({
  title,
  insights,
}: {
  title: string;
  insights: string[];
}) {
  return (
    <Card>
      <CardHeader title={title} subtitle="AI-generated · not financial advice" />
      {insights.length === 0 ? (
        <p className="py-4 text-sm text-muted">No insights available yet.</p>
      ) : (
        <ul className="space-y-2">
          {insights.map((text, i) => (
            <li key={i} className="flex gap-2 text-sm text-fg">
              <span className="text-brand">▸</span>
              <span>{text}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function SuggestionCard({ suggestion }: { suggestion: Suggestion }) {
  return (
    <Card>
      <CardHeader title="AI Suggestion" subtitle="Probabilistic — not advice" />
      <div className="flex items-center gap-3">
        <div
          className={cn(
            "inline-flex items-center rounded-lg border px-4 py-2 text-lg font-bold",
            ACTION_STYLES[suggestion.action],
          )}
        >
          {suggestion.action}
        </div>
        <div className="flex-1">
          <ConfidenceMeter value={suggestion.confidence} />
        </div>
      </div>
      <p className="mt-3 text-xs text-muted">Rationale: {suggestion.rationale}</p>
    </Card>
  );
}
