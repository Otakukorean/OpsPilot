import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createConversationMessage,
  createConversationThread,
  deleteConversationThread,
  listConversationMessages,
  listConversationThreads,
  runConversationAgent,
} from "@/features/conversations/api";

const { deleteMock, getMock, postMock } = vi.hoisted(() => ({
  deleteMock: vi.fn(),
  getMock: vi.fn(),
  postMock: vi.fn(),
}));

vi.mock("@/lib/api/client", () => ({
  apiClient: { DELETE: deleteMock, GET: getMock, POST: postMock },
}));

const thread = {
  id: "4263d9c0-feb0-4cdc-9709-94724b927895",
  title: "Synthetic investigation",
  created_at: "2026-11-07T09:00:00Z",
  updated_at: "2026-11-07T09:00:00Z",
};

const message = {
  id: "41340e08-a098-4849-8d7f-3217ac778902",
  role: "user" as const,
  body: "Review the synthetic transaction.",
  status: "stored" as const,
  created_at: "2026-11-07T09:05:00Z",
  citations: [],
};

describe("conversation API", () => {
  beforeEach(() => {
    deleteMock.mockReset();
    getMock.mockReset();
    postMock.mockReset();
  });

  it("lists owner-scoped threads without sending workspace or owner identifiers", async () => {
    const page = { items: [thread], total: 1, limit: 50, offset: 0 };
    getMock.mockResolvedValue({ data: page, response: { status: 200 } });

    await expect(listConversationThreads()).resolves.toEqual(page);

    expect(getMock).toHaveBeenCalledWith("/api/v1/chat/threads", {
      params: { query: { limit: 50, offset: 0 } },
    });
  });

  it("establishes CSRF and creates a trimmed thread with server-resolved scope", async () => {
    getMock.mockResolvedValue({ response: { ok: true, status: 204 } });
    postMock.mockResolvedValue({ data: thread, response: { status: 201 } });

    await expect(createConversationThread("  Synthetic investigation  ")).resolves.toEqual(thread);

    expect(getMock).toHaveBeenCalledWith("/api/v1/auth/csrf");
    expect(postMock).toHaveBeenCalledWith("/api/v1/chat/threads", {
      body: { title: "Synthetic investigation" },
    });
  });

  it("reads and stores messages using only the selected thread identifier", async () => {
    const page = { items: [message], total: 1, limit: 50, offset: 0 };
    getMock
      .mockResolvedValueOnce({ data: page, response: { status: 200 } })
      .mockResolvedValueOnce({ response: { ok: true, status: 204 } });
    postMock.mockResolvedValue({ data: message, response: { status: 201 } });

    await expect(listConversationMessages(thread.id)).resolves.toEqual(page);
    await expect(
      createConversationMessage(thread.id, "  Review the synthetic transaction.  "),
    ).resolves.toEqual(message);

    expect(getMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/chat/threads/{thread_id}/messages",
      {
        params: {
          path: { thread_id: thread.id },
          query: { limit: 50, offset: 0 },
        },
      },
    );
    expect(postMock).toHaveBeenCalledWith(
      "/api/v1/chat/threads/{thread_id}/messages",
      {
        params: { path: { thread_id: thread.id } },
        body: { text: "Review the synthetic transaction." },
      },
    );
  });

  it("uses CSRF protection when deleting a thread", async () => {
    getMock.mockResolvedValue({ response: { ok: true, status: 204 } });
    deleteMock.mockResolvedValue({ response: { status: 204 } });

    await expect(deleteConversationThread(thread.id)).resolves.toBeUndefined();

    expect(deleteMock).toHaveBeenCalledWith("/api/v1/chat/threads/{thread_id}", {
      params: { path: { thread_id: thread.id } },
    });
  });

  it("runs the agent directly so the user message is not stored twice", async () => {
    const run = {
      id: "9c2e99b9-0987-4395-8133-3037e464e109",
      status: "completed" as const,
      model: "synthetic-test-model",
      llm_calls: 2,
      tool_calls: 1,
      input_tokens: 30,
      output_tokens: 12,
      message: {
        ...message,
        id: "ddf0869b-0035-47ea-9268-0d641d306454",
        role: "assistant" as const,
        body: "The authorized synthetic evidence indicates a failed transaction.",
        status: "completed" as const,
      },
      citations: [],
    };
    getMock.mockResolvedValue({ response: { ok: true, status: 204 } });
    postMock.mockResolvedValue({ data: run, response: { status: 201 } });

    await expect(
      runConversationAgent(thread.id, "  Why did the synthetic transaction fail?  "),
    ).resolves.toEqual(run);

    expect(postMock).toHaveBeenCalledTimes(1);
    expect(postMock).toHaveBeenCalledWith(
      "/api/v1/chat/threads/{thread_id}/agent-runs",
      {
        params: { path: { thread_id: thread.id } },
        body: { text: "Why did the synthetic transaction fail?" },
      },
    );
  });
});
