import { useQuery } from "@tanstack/react-query";

import {
  listConversationMessages,
  listConversationThreads,
} from "@/features/conversations/api";

export const conversationKeys = {
  all: ["conversations"] as const,
  threads: ["conversations", "threads"] as const,
  messages: (threadId: string) => ["conversations", "messages", threadId] as const,
};

export function useConversationThreads() {
  return useQuery({
    queryKey: conversationKeys.threads,
    queryFn: listConversationThreads,
    retry: false,
    staleTime: 15_000,
  });
}

export function useConversationMessages(threadId: string | undefined) {
  return useQuery({
    queryKey: conversationKeys.messages(threadId ?? "none"),
    queryFn: () => listConversationMessages(threadId!),
    enabled: Boolean(threadId),
    retry: false,
    staleTime: 10_000,
  });
}
