import { beforeEach, describe, expect, it, vi } from "vitest";

import { queryTransactions } from "@/features/transactions/api";

const { getMock } = vi.hoisted(() => ({ getMock: vi.fn() }));

vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: getMock },
}));

describe("transaction API", () => {
  beforeEach(() => getMock.mockReset());

  it("sends an exact normalized code without any workspace identifier", async () => {
    const page = { items: [], total: 0, limit: 10, offset: 0 };
    getMock.mockResolvedValue({ data: page, response: { status: 200 } });

    await expect(queryTransactions({
      code: "  TXN-9001  ",
      status: "failed",
      limit: 10,
      offset: 0,
    })).resolves.toEqual(page);

    expect(getMock).toHaveBeenCalledWith("/api/v1/transactions", {
      params: {
        query: {
          code: "TXN-9001",
          status: "failed",
          limit: 10,
          offset: 0,
        },
      },
    });
  });

  it("preserves role authorization errors for the UI", async () => {
    getMock.mockResolvedValue({
      error: { message: "Operations access denied." },
      response: { status: 403 },
    });

    await expect(queryTransactions({ limit: 10, offset: 0 })).rejects.toMatchObject({
      name: "TransactionsApiError",
      message: "Operations access denied.",
      status: 403,
    });
  });
});
