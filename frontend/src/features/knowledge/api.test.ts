import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  deleteKnowledgeDocument,
  listKnowledgeDocuments,
  updateKnowledgeVisibility,
  uploadKnowledgeDocument,
} from "@/features/knowledge/api";

const { deleteMock, getMock, patchMock, postMock } = vi.hoisted(() => ({
  deleteMock: vi.fn(),
  getMock: vi.fn(),
  patchMock: vi.fn(),
  postMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: {
    DELETE: deleteMock,
    GET: getMock,
    PATCH: patchMock,
    POST: postMock,
  },
}));

const document = {
  id: "8451d851-cb12-4b15-94c5-f9a8552060ca",
  title: "Synthetic operations guide",
  original_filename: "synthetic-guide.txt",
  content_type: "text/plain",
  size_bytes: 28,
  sha256: "a".repeat(64),
  page_count: null,
  visibility: "restricted" as const,
  status: "queued" as const,
  failure_reason: "",
  version: 1,
  embedding_model: "",
  created_at: "2026-11-07T09:00:00Z",
  updated_at: "2026-11-07T09:00:00Z",
};

describe("knowledge API", () => {
  beforeEach(() => {
    deleteMock.mockReset();
    getMock.mockReset();
    patchMock.mockReset();
    postMock.mockReset();
  });

  it("lists documents without sending a workspace identifier", async () => {
    const page = { items: [document], total: 1, limit: 50, offset: 0 };
    getMock.mockResolvedValue({ data: page, response: { status: 200 } });

    await expect(listKnowledgeDocuments()).resolves.toEqual(page);

    expect(getMock).toHaveBeenCalledWith("/api/v1/documents", {
      params: { query: { limit: 50, offset: 0 } },
    });
  });

  it("uses CSRF and multipart form data for a private upload", async () => {
    const file = new File(["Synthetic knowledge"], "synthetic-guide.txt", {
      type: "text/plain",
    });
    getMock.mockResolvedValue({ response: { ok: true, status: 200 } });
    postMock.mockResolvedValue({ data: document, response: { status: 201 } });

    await expect(uploadKnowledgeDocument(file, "  Synthetic operations guide  "))
      .resolves.toEqual(document);

    expect(getMock).toHaveBeenCalledWith("/api/v1/auth/csrf");
    const [, options] = postMock.mock.calls[0];
    expect(postMock.mock.calls[0][0]).toBe("/api/v1/documents");
    expect(options.body).toEqual({
      file: "synthetic-guide.txt",
      title: "Synthetic operations guide",
    });
    const formData = options.bodySerializer();
    expect(formData).toBeInstanceOf(FormData);
    expect(formData.get("file")).toBe(file);
    expect(formData.get("title")).toBe("Synthetic operations guide");
    expect(formData.has("workspace")).toBe(false);
  });

  it("publishes and deletes by document ID with CSRF and no workspace field", async () => {
    const published = { ...document, visibility: "viewer" as const };
    getMock.mockResolvedValue({ response: { ok: true, status: 200 } });
    patchMock.mockResolvedValue({ data: published, response: { status: 200 } });
    deleteMock.mockResolvedValue({ response: { status: 204 } });

    await expect(updateKnowledgeVisibility(document.id, "viewer")).resolves.toEqual(published);
    await expect(deleteKnowledgeDocument(document.id)).resolves.toBeUndefined();

    expect(patchMock).toHaveBeenCalledWith(
      "/api/v1/documents/{document_id}/visibility",
      {
        params: { path: { document_id: document.id } },
        body: { visibility: "viewer" },
      },
    );
    expect(deleteMock).toHaveBeenCalledWith("/api/v1/documents/{document_id}", {
      params: { path: { document_id: document.id } },
    });
  });
});
