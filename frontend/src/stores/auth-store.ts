import { create } from "zustand";

import type { components } from "@/lib/api/schema";

export type AuthUser = components["schemas"]["UserContextOut"];
export type AuthStatus =
  | "idle"
  | "loading"
  | "authenticated"
  | "anonymous"
  | "error";

type AuthState = {
  status: AuthStatus;
  user: AuthUser | null;
  setStatus: (status: AuthStatus) => void;
  setUser: (user: AuthUser) => void;
  clearUser: () => void;
};

export const useAuthStore = create<AuthState>((set) => ({
  status: "idle",
  user: null,
  setStatus: (status) => set({ status }),
  setUser: (user) => set({ status: "authenticated", user }),
  clearUser: () => set({ status: "anonymous", user: null }),
}));
