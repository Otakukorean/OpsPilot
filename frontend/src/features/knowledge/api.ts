import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type KnowledgeDocument = components["schemas"]["DocumentOut"];
export type KnowledgeDocumentPage = components["schemas"]["DocumentPageOut"];
export type KnowledgeVisibility = KnowledgeDocument["visibility"];

type SafeApiError = { message?: string };

export class KnowledgeApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "KnowledgeApiError";
  }
}

function safeMessage(error: unknown, fallback: string): string {
  if (error && typeof error === "object" && "message" in error) {
    const message = (error as SafeApiError).message;
    if (typeof message === "string" && message.trim()) return message;
  }
  return fallback;
}

async function ensureCsrfCookie() {
  const { response } = await apiClient.GET("/api/v1/auth/csrf");
  if (!response.ok) {
    throw new KnowledgeApiError("Unable to establish a secure session.", response.status);
  }
}

export async function listKnowledgeDocuments(): Promise<KnowledgeDocumentPage> {
  const { data, error, response } = await apiClient.GET("/api/v1/documents", {
    params: { query: { limit: 50, offset: 0 } },
  });
  if (!data) {
    throw new KnowledgeApiError(
      safeMessage(error, "Unable to load knowledge documents."),
      response.status,
    );
  }
  return data;
}

export async function uploadKnowledgeDocument(
  file: File,
  title: string,
): Promise<KnowledgeDocument> {
  await ensureCsrfCookie();
  const formData = new FormData();
  formData.set("file", file);
  if (title.trim()) formData.set("title", title.trim());

  const { data, error, response } = await apiClient.POST("/api/v1/documents", {
    body: { file: file.name, title: title.trim() },
    bodySerializer: () => formData,
  });
  if (!data) {
    throw new KnowledgeApiError(
      safeMessage(error, "Unable to upload the document."),
      response.status,
    );
  }
  return data;
}

export async function updateKnowledgeVisibility(
  documentId: string,
  visibility: KnowledgeVisibility,
): Promise<KnowledgeDocument> {
  await ensureCsrfCookie();
  const { data, error, response } = await apiClient.PATCH(
    "/api/v1/documents/{document_id}/visibility",
    {
      params: { path: { document_id: documentId } },
      body: { visibility },
    },
  );
  if (!data) {
    throw new KnowledgeApiError(
      safeMessage(error, "Unable to update document visibility."),
      response.status,
    );
  }
  return data;
}

export async function deleteKnowledgeDocument(documentId: string): Promise<void> {
  await ensureCsrfCookie();
  const { error, response } = await apiClient.DELETE(
    "/api/v1/documents/{document_id}",
    { params: { path: { document_id: documentId } } },
  );
  if (error) {
    throw new KnowledgeApiError(
      safeMessage(error, "Unable to delete the document."),
      response.status,
    );
  }
}
