"use client";

import { useRouter } from "next/navigation";
import { useCallback } from "react";

import { authApi, type RegisterPayload } from "@/services/api/auth.api";
import { useAuthStore } from "@/store/auth.store";
import { ROUTES } from "@/utils/constants";

/** Thin controller around the auth store for use inside components. */
export function useAuth() {
  const router = useRouter();
  const { user, status, loginWithTokens, logout } = useAuthStore();

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await authApi.login(email, password);
      await loginWithTokens(tokens.access_token, tokens.refresh_token);
      router.push(ROUTES.dashboard);
    },
    [loginWithTokens, router],
  );

  const signup = useCallback(
    async (payload: RegisterPayload) => {
      await authApi.register(payload);
      // Auto-login right after a successful registration.
      const tokens = await authApi.login(payload.email, payload.password);
      await loginWithTokens(tokens.access_token, tokens.refresh_token);
      router.push(ROUTES.dashboard);
    },
    [loginWithTokens, router],
  );

  const signOut = useCallback(() => {
    logout();
    router.push(ROUTES.login);
  }, [logout, router]);

  return {
    user,
    status,
    isAuthenticated: status === "authenticated",
    login,
    signup,
    signOut,
  };
}
