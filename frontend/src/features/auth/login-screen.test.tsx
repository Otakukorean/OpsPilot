import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { login } from "@/features/auth/api";
import { LoginScreen } from "@/features/auth/login-screen";
import type { AuthUser } from "@/stores/auth-store";
import { useAuthStore } from "@/stores/auth-store";

const { replaceMock } = vi.hoisted(() => ({ replaceMock: vi.fn() }));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: replaceMock }),
}));

vi.mock("@/features/auth/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/auth/api")>();
  return { ...original, login: vi.fn() };
});

const user: AuthUser = {
  id: "a2ea3576-a1e9-43d8-9aa3-4bc1c8c85bd1",
  email: "analyst@example.test",
  first_name: "Synthetic",
  last_name: "Analyst",
  membership: {
    role: "analyst",
    workspace: {
      id: "3ba85713-6aa7-4314-a4fb-0a6684a49d26",
      name: "Northstar Demo",
    },
  },
};

function TestProviders({ children }: Readonly<{ children: ReactNode }>) {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("LoginScreen", () => {
  beforeEach(() => {
    replaceMock.mockReset();
    vi.mocked(login).mockReset();
    useAuthStore.setState({ status: "anonymous", user: null });
  });

  it("validates required credentials before sending a request", async () => {
    render(<LoginScreen />, { wrapper: TestProviders });

    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByText("Enter your email address.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });

  it("stores the returned user context and enters the authenticated app", async () => {
    vi.mocked(login).mockResolvedValue(user);
    render(<LoginScreen />, { wrapper: TestProviders });

    fireEvent.change(screen.getByLabelText("Email address"), {
      target: { value: "analyst@example.test" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "synthetic-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Continue" }));

    await waitFor(() => {
      expect(login).toHaveBeenCalled();
    });
    expect(vi.mocked(login).mock.calls[0]?.[0]).toEqual({
      email: "analyst@example.test",
      password: "synthetic-password",
    });
    expect(useAuthStore.getState().user).toEqual(user);
    expect(replaceMock).toHaveBeenCalledWith("/app");
  });

  it("shows and signs in with the public synthetic tester account", async () => {
    vi.mocked(login).mockResolvedValue(user);
    const demoCredentials = {
      email: "tester@atlaspay.example",
      password: "public-synthetic-tester-password",
    };
    render(<LoginScreen demoCredentials={demoCredentials} />, { wrapper: TestProviders });

    expect(screen.getByText(demoCredentials.email)).toBeInTheDocument();
    expect(screen.getByText(demoCredentials.password)).toBeInTheDocument();
    expect(screen.getByText("No admin permissions.", { exact: false })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Sign in as demo analyst" }));

    await waitFor(() => {
      expect(vi.mocked(login).mock.calls[0]?.[0]).toEqual(demoCredentials);
    });
    expect(screen.getByLabelText("Email address")).toHaveValue(demoCredentials.email);
    expect(screen.getByLabelText("Password")).toHaveValue(demoCredentials.password);
  });
});
