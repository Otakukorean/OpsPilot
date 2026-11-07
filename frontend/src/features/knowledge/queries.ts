import { useQuery } from "@tanstack/react-query";

import {
  KnowledgeApiError,
  listKnowledgeDocuments,
} from "@/features/knowledge/api";

export const knowledgeKeys = {
  all: ["knowledge"] as const,
  documents: ["knowledge", "documents"] as const,
};

export function useKnowledgeDocuments() {
  return useQuery({
    queryKey: knowledgeKeys.documents,
    queryFn: listKnowledgeDocuments,
    refetchInterval(query) {
      const isIngesting = query.state.data?.items.some((document) =>
        document.status === "queued" || document.status === "processing",
      );
      return isIngesting ? 2_000 : false;
    },
    retry(failureCount, error) {
      if (error instanceof KnowledgeApiError && [401, 403].includes(error.status)) {
        return false;
      }
      return failureCount < 1;
    },
    staleTime: 15_000,
  });
}
