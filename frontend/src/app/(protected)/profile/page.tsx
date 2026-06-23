"use client";

import { NotificationSettings } from "@/components/mobile/NotificationSettings";
import { Badge, Button, Card, CardHeader } from "@/components/ui";
import { useAuth } from "@/hooks/useAuth";
import { useWatchlist } from "@/hooks/useWatchlist";
import { formatDateTime } from "@/utils/format";

export default function ProfilePage() {
  const { user, signOut } = useAuth();
  const { count } = useWatchlist();

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <h1 className="text-2xl font-bold text-fg">Profile</h1>

      <Card>
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand/15 text-2xl font-bold text-brand">
            {(user?.email[0] ?? "U").toUpperCase()}
          </div>
          <div>
            <p className="text-lg font-semibold text-fg">{user?.email}</p>
            <Badge tone="brand" className="mt-1 capitalize">
              {user?.role}
            </Badge>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader title="Account Details" />
        <div className="space-y-2 text-sm">
          <div className="flex justify-between border-b border-border/60 py-2">
            <span className="text-muted">Email</span>
            <span className="text-fg">{user?.email}</span>
          </div>
          <div className="flex justify-between border-b border-border/60 py-2">
            <span className="text-muted">Role</span>
            <span className="capitalize text-fg">{user?.role}</span>
          </div>
          <div className="flex justify-between border-b border-border/60 py-2">
            <span className="text-muted">Status</span>
            <span className="text-fg">{user?.is_active ? "Active" : "Disabled"}</span>
          </div>
          <div className="flex justify-between border-b border-border/60 py-2">
            <span className="text-muted">Member since</span>
            <span className="text-fg">{formatDateTime(user?.created_at)}</span>
          </div>
          <div className="flex justify-between py-2">
            <span className="text-muted">Watchlist size</span>
            <span className="text-fg">{count}</span>
          </div>
        </div>
      </Card>

      <NotificationSettings />

      <Button variant="danger" onClick={signOut}>
        Sign out
      </Button>
    </div>
  );
}
