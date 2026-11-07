"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Eye, EyeOff, LoaderCircle, LockKeyhole, ShieldCheck, UserRoundCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { login } from "@/features/auth/api";
import { currentUserQueryKey } from "@/features/auth/auth-bootstrap";
import { useAuthStore } from "@/stores/auth-store";

const loginSchema = z.object({
  email: z.string().trim().min(1, "Enter your email address.").email("Enter a valid email address."),
  password: z.string().min(1, "Enter your password.").max(128, "Password is too long."),
});

type LoginFormValues = z.infer<typeof loginSchema>;

const environmentDemoCredentials =
  process.env.NEXT_PUBLIC_DEMO_EMAIL && process.env.NEXT_PUBLIC_DEMO_PASSWORD
    ? {
        email: process.env.NEXT_PUBLIC_DEMO_EMAIL,
        password: process.env.NEXT_PUBLIC_DEMO_PASSWORD,
      }
    : undefined;

type LoginScreenProps = {
  demoCredentials?: LoginFormValues;
};

export function LoginScreen({ demoCredentials = environmentDemoCredentials }: LoginScreenProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const status = useAuthStore((state) => state.status);
  const setUser = useAuthStore((state) => state.setUser);
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  const loginMutation = useMutation({
    mutationFn: login,
    onSuccess(user) {
      setUser(user);
      queryClient.setQueryData(currentUserQueryKey, user);
      router.replace("/app");
    },
  });

  useEffect(() => {
    if (status === "authenticated") {
      router.replace("/app");
    }
  }, [router, status]);

  const onSubmit = handleSubmit((values) => {
    loginMutation.reset();
    loginMutation.mutate(values);
  });

  const useDemoAccount = () => {
    if (!demoCredentials) return;
    loginMutation.reset();
    reset(demoCredentials);
    loginMutation.mutate(demoCredentials);
  };

  return (
    <main className="flex min-h-screen items-center justify-center px-5 py-10 sm:px-8">
      <section
        aria-labelledby="login-title"
        className="relative w-full max-w-[440px] overflow-hidden border border-[#cdd3ca] bg-[#fbfcf8] shadow-[0_24px_70px_rgba(23,32,29,0.12)]"
      >
        <div className="flex h-9 items-center gap-2 border-b border-[#d9ded6] bg-[#f0f3ed] px-5 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#52615c]">
          <span className="relative flex size-2" aria-hidden="true">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-600 opacity-40" />
            <span className="relative inline-flex size-2 rounded-full bg-emerald-700" />
          </span>
          Secure session
          <span className="ml-auto font-mono tracking-normal text-[#7b8782]">TLS / CSRF</span>
        </div>

        <div className="px-6 py-8 sm:px-10 sm:py-10">
          <div className="mb-8">
            <div className="mb-6 flex size-11 items-center justify-center border border-[#bfc8c0] bg-white text-[#176b50] shadow-sm">
              <ShieldCheck aria-hidden="true" size={23} strokeWidth={1.8} />
            </div>
            <p className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-[#176b50]">OpsPilot</p>
            <h1 id="login-title" className="text-[2rem] font-semibold leading-tight tracking-[-0.035em] text-[#17201d]">
              Sign in to your workspace
            </h1>
            <p className="mt-3 text-sm leading-6 text-[#65716d]">
              Use your organization account to continue.
            </p>
          </div>

          <form className="space-y-5" noValidate onSubmit={onSubmit}>
            <div>
              <label className="mb-2 block text-sm font-semibold text-[#293530]" htmlFor="email">
                Email address
              </label>
              <input
                {...register("email")}
                aria-describedby={errors.email ? "email-error" : undefined}
                aria-invalid={Boolean(errors.email)}
                autoComplete="username"
                className="h-12 w-full border border-[#bdc5bd] bg-white px-3.5 text-base text-[#17201d] shadow-[inset_0_1px_2px_rgba(23,32,29,0.04)] transition-colors placeholder:text-[#97a09c] hover:border-[#929e96] focus:border-[#176b50] focus:outline-none"
                id="email"
                inputMode="email"
                placeholder="you@company.com"
                type="email"
              />
              {errors.email ? <p className="mt-1.5 text-sm text-[#a33b32]" id="email-error">{errors.email.message}</p> : null}
            </div>

            <div>
              <label className="mb-2 block text-sm font-semibold text-[#293530]" htmlFor="password">
                Password
              </label>
              <div className="relative">
                <input
                  {...register("password")}
                  aria-describedby={errors.password ? "password-error" : undefined}
                  aria-invalid={Boolean(errors.password)}
                  autoComplete="current-password"
                  className="h-12 w-full border border-[#bdc5bd] bg-white px-3.5 pr-12 text-base text-[#17201d] shadow-[inset_0_1px_2px_rgba(23,32,29,0.04)] transition-colors placeholder:text-[#97a09c] hover:border-[#929e96] focus:border-[#176b50] focus:outline-none"
                  id="password"
                  placeholder="Enter your password"
                  type={showPassword ? "text" : "password"}
                />
                <button
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  className="absolute inset-y-0 right-0 flex w-12 items-center justify-center text-[#65716d] transition-colors hover:text-[#17201d]"
                  onClick={() => setShowPassword((visible) => !visible)}
                  type="button"
                >
                  {showPassword ? <EyeOff aria-hidden="true" size={19} /> : <Eye aria-hidden="true" size={19} />}
                </button>
              </div>
              {errors.password ? <p className="mt-1.5 text-sm text-[#a33b32]" id="password-error">{errors.password.message}</p> : null}
            </div>

            {loginMutation.isError ? (
              <div className="border-l-2 border-[#b94b40] bg-[#fbefec] px-3.5 py-3 text-sm leading-5 text-[#7d2f29]" role="alert">
                {loginMutation.error.message || "Unable to sign in. Please try again."}
              </div>
            ) : null}

            <button
              className="group flex h-12 w-full items-center justify-center gap-2 bg-[#176b50] px-4 text-sm font-bold text-white shadow-[0_8px_20px_rgba(23,107,80,0.2)] transition-colors hover:bg-[#0f533d] disabled:cursor-not-allowed disabled:bg-[#7b958a]"
              disabled={loginMutation.isPending}
              type="submit"
            >
              {loginMutation.isPending ? (
                <><LoaderCircle aria-hidden="true" className="animate-spin" size={18} /> Signing in…</>
              ) : (
                <>Continue <ArrowRight aria-hidden="true" className="transition-transform group-hover:translate-x-0.5" size={18} /></>
              )}
            </button>
          </form>

          {demoCredentials ? (
            <section aria-labelledby="demo-account-title" className="mt-7 border border-[#c7d7ce] bg-[#f0f6f2] p-4">
              <div className="flex items-start gap-3">
                <span className="flex size-8 shrink-0 items-center justify-center bg-white text-[#176b50] shadow-sm"><UserRoundCheck aria-hidden="true" size={17} /></span>
                <div className="min-w-0 flex-1">
                  <h2 className="text-sm font-bold text-[#244238]" id="demo-account-title">Try the portfolio demo</h2>
                  <p className="mt-1 text-xs leading-5 text-[#66766f]">Public Analyst access to synthetic data. No admin permissions.</p>
                </div>
              </div>
              <dl className="mt-3 grid gap-1.5 border-y border-[#d9e4dd] py-3 text-xs">
                <div className="grid grid-cols-[68px_minmax(0,1fr)] gap-2"><dt className="font-semibold text-[#718078]">Email</dt><dd className="truncate font-mono text-[#294a3f]">{demoCredentials.email}</dd></div>
                <div className="grid grid-cols-[68px_minmax(0,1fr)] gap-2"><dt className="font-semibold text-[#718078]">Password</dt><dd className="truncate font-mono text-[#294a3f]">{demoCredentials.password}</dd></div>
              </dl>
              <button className="mt-3 flex h-10 w-full items-center justify-center gap-2 border border-[#8eb3a2] bg-white text-xs font-bold text-[#176b50] transition-colors hover:bg-[#e5f0e9] disabled:cursor-not-allowed disabled:opacity-60" disabled={loginMutation.isPending} onClick={useDemoAccount} type="button">
                {loginMutation.isPending ? <><LoaderCircle aria-hidden="true" className="animate-spin" size={15} /> Signing in…</> : <>Sign in as demo analyst <ArrowRight aria-hidden="true" size={15} /></>}
              </button>
            </section>
          ) : null}

          <div className="mt-7 flex items-center gap-2 border-t border-[#e0e3dc] pt-5 text-xs leading-5 text-[#72807a]">
            <LockKeyhole aria-hidden="true" className="shrink-0" size={15} />
            Your session is protected by a secure, HttpOnly cookie.
          </div>
        </div>
      </section>
    </main>
  );
}
