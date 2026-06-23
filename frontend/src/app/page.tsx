"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { LoaderOverlay } from "@/components/ui";
import { useAuthStore } from "@/store/auth.store";
import { ROUTES } from "@/utils/constants";

/** Entry route: send users to the dashboard or login based on session state. */
export default function Home() {
  const router = useRouter();
  const status = useAuthStore((s) => s.status);

  useEffect(() => {
    if (status === "authenticated") router.replace(ROUTES.dashboard);
    else if (status === "unauthenticated") router.replace(ROUTES.login);
  }, [status, router]);

  return <LoaderOverlay label="Loading…" />;
}
