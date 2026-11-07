"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { AuthApiError, getCurrentUser } from "@/features/auth/api";
import { useAuthStore } from "@/stores/auth-store";

export const currentUserQueryKey = ["auth", "current-user"] as const;

export function AuthBootstrap() {
  const setStatus = useAuthStore((state) => state.setStatus);
  const setUser = useAuthStore((state) => state.setUser);
  const clearUser = useAuthStore((state) => state.clearUser);

  const currentUser = useQuery({
    queryKey: currentUserQueryKey,
    queryFn: getCurrentUser,
    retry: false,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (currentUser.isPending) {
      setStatus("loading");
      return;
    }

    if (currentUser.data) {
      setUser(currentUser.data);
      return;
    }

    if (currentUser.error instanceof AuthApiError && currentUser.error.status === 401) {
      clearUser();
      return;
    }

    if (currentUser.error) {
      setStatus("error");
    }
  }, [clearUser, currentUser.data, currentUser.error, currentUser.isPending, setStatus, setUser]);

  return null;
}
