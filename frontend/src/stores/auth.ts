"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { User } from "@/lib/types";

interface AuthState {
  token: string | null;
  user: User | null;
  /** true после завершения persist.rehydrate() из localStorage (StoreHydrator). */
  hydrated: boolean;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
  setHydrated: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      hydrated: false,
      setAuth: (token, user) => set({ token, user }),
      logout: () => set({ token: null, user: null }),
      setHydrated: () => set({ hydrated: true }),
    }),
    {
      name: "qcs-auth",
      skipHydration: true,
      // В localStorage — только данные сессии, без служебного флага hydrated
      partialize: (state) => ({ token: state.token, user: state.user }),
    },
  ),
);
