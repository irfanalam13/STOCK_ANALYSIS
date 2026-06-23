// Single source of truth for JWT storage. Kept separate from the Zustand auth
// store so the Axios layer can read/write tokens without importing React state.
import { STORAGE_KEYS } from "@/utils/constants";

const isBrowser = typeof window !== "undefined";

export const tokenStore = {
  getAccess(): string | null {
    return isBrowser ? localStorage.getItem(STORAGE_KEYS.accessToken) : null;
  },
  getRefresh(): string | null {
    return isBrowser ? localStorage.getItem(STORAGE_KEYS.refreshToken) : null;
  },
  set(access: string, refresh: string): void {
    if (!isBrowser) return;
    localStorage.setItem(STORAGE_KEYS.accessToken, access);
    localStorage.setItem(STORAGE_KEYS.refreshToken, refresh);
  },
  clear(): void {
    if (!isBrowser) return;
    localStorage.removeItem(STORAGE_KEYS.accessToken);
    localStorage.removeItem(STORAGE_KEYS.refreshToken);
  },
};
