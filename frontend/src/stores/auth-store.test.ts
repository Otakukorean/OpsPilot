import { beforeEach, describe, expect, it } from "vitest";

import type { AuthUser } from "@/stores/auth-store";
import { useAuthStore } from "@/stores/auth-store";

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

describe("auth store", () => {
  beforeEach(() => {
    useAuthStore.setState({ status: "idle", user: null });
  });

  it("keeps the server-provided user context in memory", () => {
    useAuthStore.getState().setUser(user);

    expect(useAuthStore.getState()).toMatchObject({
      status: "authenticated",
      user,
    });
  });

  it("clears user context when the session ends", () => {
    useAuthStore.getState().setUser(user);
    useAuthStore.getState().clearUser();

    expect(useAuthStore.getState()).toMatchObject({
      status: "anonymous",
      user: null,
    });
  });
});
