import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type LoginCredentials = components["schemas"]["LoginIn"];
export type UserContext = components["schemas"]["UserContextOut"];

type SafeApiError = {
  message?: string;
};

export class AuthApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "AuthApiError";
  }
}

function getSafeMessage(error: unknown, fallback: string): string {
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as SafeApiError).message;
    if (typeof message === "string" && message.trim()) {
      return message;
    }
  }
  return fallback;
}

async function ensureCsrfCookie(): Promise<void> {
  const { response } = await apiClient.GET("/api/v1/auth/csrf");
  if (!response.ok) {
    throw new AuthApiError(
      "Unable to establish a secure session.",
      response.status,
    );
  }
}

export async function login(credentials: LoginCredentials): Promise<UserContext> {
  await ensureCsrfCookie();

  const { data, error, response } = await apiClient.POST("/api/v1/auth/login", {
    body: credentials,
  });

  if (!data) {
    throw new AuthApiError(
      getSafeMessage(error, "Unable to sign in with those credentials."),
      response.status,
    );
  }

  return data;
}

export async function getCurrentUser(): Promise<UserContext> {
  const { data, error, response } = await apiClient.GET("/api/v1/me");

  if (!data) {
    throw new AuthApiError(
      getSafeMessage(error, "Unable to restore your session."),
      response.status,
    );
  }

  return data;
}

export async function logout(): Promise<void> {
  await ensureCsrfCookie();

  const { error, response } = await apiClient.POST("/api/v1/auth/logout");
  if (error) {
    throw new AuthApiError(
      getSafeMessage(error, "Unable to sign out. Please try again."),
      response.status,
    );
  }
}
