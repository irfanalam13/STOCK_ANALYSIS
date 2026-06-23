"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  mobileApi,
  type NotificationPreferences,
} from "@/services/api/mobile.api";

const PREFS_KEY = ["mobile", "preferences"] as const;

export function useNotificationPreferences() {
  return useQuery({
    queryKey: PREFS_KEY,
    queryFn: mobileApi.getPreferences,
  });
}

export function useUpdatePreferences() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (prefs: NotificationPreferences) =>
      mobileApi.updatePreferences(prefs),
    onSuccess: (data) => qc.setQueryData(PREFS_KEY, data),
  });
}

/** Single aggregated mobile home payload (overview + watchlist + portfolio). */
export function useMobileHome() {
  return useQuery({
    queryKey: ["mobile", "home"],
    queryFn: mobileApi.home,
    refetchInterval: 30_000,
  });
}
