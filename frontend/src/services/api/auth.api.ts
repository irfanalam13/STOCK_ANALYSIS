import type { TokenPair, User, UserRole } from "@/types";
import { api } from "./axios";

export interface RegisterPayload {
  email: string;
  password: string;
  role?: UserRole;
}

export const authApi = {
  async register(payload: RegisterPayload): Promise<User> {
    const { data } = await api.post<User>("/auth/register", payload);
    return data;
  },
  async login(email: string, password: string): Promise<TokenPair> {
    const { data } = await api.post<TokenPair>("/auth/login", {
      email,
      password,
    });
    return data;
  },
  async me(): Promise<User> {
    const { data } = await api.get<User>("/users/me");
    return data;
  },
};
