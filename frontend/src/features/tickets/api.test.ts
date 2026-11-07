import { beforeEach, describe, expect, it, vi } from "vitest";

import { searchTickets } from "@/features/tickets/api";

const { getMock } = vi.hoisted(() => ({ getMock: vi.fn() }));

vi.mock("@/lib/api/client", () => ({
  apiClient: { GET: getMock },
}));

describe("ticket API", () => {
  beforeEach(() => getMock.mockReset());

  it("sends only allowlisted query fields and never a workspace identifier", async () => {
    const page = { items: [], total: 0, limit: 10, offset: 0 };
    getMock.mockResolvedValue({ data: page, response: { status: 200 } });

    await expect(searchTickets({
      query: "  TKT-2001  ",
      status: "open",
      limit: 10,
      offset: 0,
    })).resolves.toEqual(page);

    expect(getMock).toHaveBeenCalledWith("/api/v1/tickets", {
      params: {
        query: {
          query: "TKT-2001",
          status: "open",
          limit: 10,
          offset: 0,
        },
      },
    });
  });

  it("preserves an authorization failure for the role-aware UI", async () => {
    getMock.mockResolvedValue({
      error: { message: "Operations access denied." },
      response: { status: 403 },
    });

    await expect(searchTickets({ limit: 10, offset: 0 })).rejects.toMatchObject({
      name: "TicketsApiError",
      message: "Operations access denied.",
      status: 403,
    });
  });
});
