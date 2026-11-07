import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
  queryTransactions,
  type TransactionQueryParams,
  TransactionsApiError,
} from "@/features/transactions/api";

export const transactionsQueryKey = (params: TransactionQueryParams) =>
  ["transactions", params] as const;

export function useTransactions(params: TransactionQueryParams) {
  return useQuery({
    queryKey: transactionsQueryKey(params),
    queryFn: () => queryTransactions(params),
    placeholderData: keepPreviousData,
    retry(failureCount, error) {
      if (error instanceof TransactionsApiError && [401, 403].includes(error.status)) {
        return false;
      }
      return failureCount < 1;
    },
    staleTime: 30_000,
  });
}
