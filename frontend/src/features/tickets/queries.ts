import { keepPreviousData, useQuery } from "@tanstack/react-query";

import {
  searchTickets,
  type TicketSearchParams,
  TicketsApiError,
} from "@/features/tickets/api";

export const ticketsQueryKey = (params: TicketSearchParams) =>
  ["tickets", params] as const;

export function useTickets(params: TicketSearchParams) {
  return useQuery({
    queryKey: ticketsQueryKey(params),
    queryFn: () => searchTickets(params),
    placeholderData: keepPreviousData,
    retry(failureCount, error) {
      if (error instanceof TicketsApiError && [401, 403].includes(error.status)) {
        return false;
      }
      return failureCount < 1;
    },
    staleTime: 30_000,
  });
}
