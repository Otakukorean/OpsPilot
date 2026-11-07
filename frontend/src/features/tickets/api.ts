import { apiClient } from "@/lib/api/client";
import type { components, operations } from "@/lib/api/schema";

export type Ticket = components["schemas"]["TicketOut"];
export type TicketPage = components["schemas"]["TicketPageOut"];
export type TicketSearchParams = NonNullable<
  operations["searchTickets"]["parameters"]["query"]
>;

type SafeApiError = { message?: string };

export class TicketsApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "TicketsApiError";
  }
}

function safeMessage(error: unknown): string {
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as SafeApiError).message;
    if (typeof message === "string" && message.trim()) return message;
  }
  return "Unable to load tickets. Please try again.";
}

export async function searchTickets(params: TicketSearchParams): Promise<TicketPage> {
  const query = params.query?.trim();
  const { data, error, response } = await apiClient.GET("/api/v1/tickets", {
    params: {
      query: {
        ...params,
        query: query || undefined,
      },
    },
  });

  if (!data) {
    throw new TicketsApiError(safeMessage(error), response.status);
  }

  return data;
}
