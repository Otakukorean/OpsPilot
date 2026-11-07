import { apiClient } from "@/lib/api/client";
import type { components, operations } from "@/lib/api/schema";

export type Transaction = components["schemas"]["TransactionOut"];
export type TransactionPage = components["schemas"]["TransactionPageOut"];
export type TransactionQueryParams = NonNullable<
  operations["queryTransactions"]["parameters"]["query"]
>;

type SafeApiError = { message?: string };

export class TransactionsApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "TransactionsApiError";
  }
}

function safeMessage(error: unknown): string {
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as SafeApiError).message;
    if (typeof message === "string" && message.trim()) return message;
  }
  return "Unable to load transactions. Please try again.";
}

export async function queryTransactions(
  params: TransactionQueryParams,
): Promise<TransactionPage> {
  const code = params.code?.trim();
  const { data, error, response } = await apiClient.GET("/api/v1/transactions", {
    params: {
      query: {
        ...params,
        code: code || undefined,
      },
    },
  });

  if (!data) {
    throw new TransactionsApiError(safeMessage(error), response.status);
  }

  return data;
}
