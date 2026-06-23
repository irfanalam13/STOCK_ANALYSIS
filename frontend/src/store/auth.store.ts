import { create } from "zustand";

import { authApi } from "@/services/api/auth.api";
import { setAuthFailureHandler } from "@/services/api/axios";
import { tokenStore } from "@/services/api/tokenStore";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  status: "idle" | "loading" | "authenticated" | "unauthenticated";
  setUser: (user: User | null) => void;
  /** Persist tokens then hydrate the current user. */
  loginWithTokens: (access: string, refresh: string) => Promise<void>;
  /** Load the session from a stored token on app boot. */
  bootstrap: () => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  status: "idle",

  setUser: (user) =>
    set({ user, status: user ? "authenticated" : "unauthenticated" }),

  loginWithTokens: async (access, refresh) => {
    tokenStore.set(access, refresh);
    set({ status: "loading" });
    const user = await authApi.me();
    set({ user, status: "authenticated" });
  },

  bootstrap: async () => {
    if (!tokenStore.getAccess()) {
      set({ status: "unauthenticated" });
      return;
    }
    set({ status: "loading" });
    try {
      const user = await authApi.me();
      set({ user, status: "authenticated" });
    } catch {
      tokenStore.clear();
      set({ user: null, status: "unauthenticated" });
    }
  },

  logout: () => {
    tokenStore.clear();
    set({ user: null, status: "unauthenticated" });
  },
}));

// Wire the Axios layer's forced-logout signal to the store (auto-logout on
// refresh failure / token expiry).
setAuthFailureHandler(() => useAuthStore.getState().logout());
