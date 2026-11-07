"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { logout } from "@/features/auth/api";
import { currentUserQueryKey } from "@/features/auth/auth-bootstrap";
import { MockOpsPilotApp } from "@/features/dashboard/mock-app";
import { useAuthStore } from "@/stores/auth-store";

export default function AuthenticatedAppPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const status = useAuthStore((state) => state.status);
  const user = useAuthStore((state) => state.user);
  const clearUser = useAuthStore((state) => state.clearUser);
  const setStatus = useAuthStore((state) => state.setStatus);

  const logoutMutation = useMutation({
    mutationFn: logout,
    onSuccess() {
      clearUser();
      queryClient.removeQueries({ queryKey: currentUserQueryKey });
      router.replace("/");
    },
  });

  useEffect(() => {
    if (status === "anonymous") {
      router.replace("/");
    }
  }, [router, status]);

  if (status === "idle" || status === "loading") {
    return (
      <main className="grid min-h-screen place-items-center px-6">
        <p className="flex items-center gap-2 text-sm text-[#65716d]" role="status">
          <LoaderCircle aria-hidden="true" className="animate-spin" size={17} /> Checking session…
        </p>
      </main>
    );
  }

  if (status === "error" && !user) {
    return (
      <main className="grid min-h-screen place-items-center px-6">
        <section className="max-w-sm border border-[#cdd3ca] bg-[#fbfcf8] p-7 text-center shadow-[0_20px_60px_rgba(23,32,29,0.1)]" role="alert">
          <h1 className="text-xl font-semibold tracking-[-0.02em]">Unable to verify your session</h1>
          <p className="mt-2 text-sm leading-6 text-[#65716d]">Check your connection, then try again.</p>
          <button
            className="mt-5 h-11 bg-[#176b50] px-5 text-sm font-bold text-white transition-colors hover:bg-[#0f533d]"
            onClick={() => {
              setStatus("loading");
              void queryClient.invalidateQueries({ queryKey: currentUserQueryKey });
            }}
            type="button"
          >
            Retry
          </button>
        </section>
      </main>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <MockOpsPilotApp
      isLoggingOut={logoutMutation.isPending}
      logoutError={logoutMutation.isError ? logoutMutation.error.message : undefined}
      onLogout={() => logoutMutation.mutate()}
      user={user}
    />
  );
}
