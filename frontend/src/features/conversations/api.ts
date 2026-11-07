import { apiClient } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ConversationThread = components["schemas"]["ThreadOut"];
export type ConversationThreadPage = components["schemas"]["ThreadPageOut"];
export type ConversationMessage = components["schemas"]["MessageOut"];
export type ConversationMessagePage = components["schemas"]["MessagePageOut"];
export type ConversationAgentRun = components["schemas"]["AgentRunOut"];

type SafeApiError = { message?: string };

export class ConversationsApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ConversationsApiError";
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
    throw new ConversationsApiError("Unable to establish a secure session.", response.status);
  }
}

export async function listConversationThreads(): Promise<ConversationThreadPage> {
  const { data, error, response } = await apiClient.GET("/api/v1/chat/threads", {
    params: { query: { limit: 50, offset: 0 } },
  });
  if (!data) {
    throw new ConversationsApiError(
      safeMessage(error, "Unable to load conversations."),
      response.status,
    );
  }
  return data;
}

export async function createConversationThread(title: string): Promise<ConversationThread> {
  await ensureCsrfCookie();
  const { data, error, response } = await apiClient.POST("/api/v1/chat/threads", {
    body: { title: title.trim() },
  });
  if (!data) {
    throw new ConversationsApiError(
      safeMessage(error, "Unable to create the conversation."),
      response.status,
    );
  }
  return data;
}

export async function listConversationMessages(
  threadId: string,
): Promise<ConversationMessagePage> {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/chat/threads/{thread_id}/messages",
    {
      params: {
        path: { thread_id: threadId },
        query: { limit: 50, offset: 0 },
      },
    },
  );
  if (!data) {
    throw new ConversationsApiError(
      safeMessage(error, "Unable to load conversation messages."),
      response.status,
    );
  }
  return data;
}

export async function createConversationMessage(
  threadId: string,
  text: string,
): Promise<ConversationMessage> {
  await ensureCsrfCookie();
  const { data, error, response } = await apiClient.POST(
    "/api/v1/chat/threads/{thread_id}/messages",
    {
      params: { path: { thread_id: threadId } },
      body: { text: text.trim() },
    },
  );
  if (!data) {
    throw new ConversationsApiError(
      safeMessage(error, "Unable to store your message."),
      response.status,
    );
  }
  return data;
}

export async function runConversationAgent(
  threadId: string,
  text: string,
): Promise<ConversationAgentRun> {
  await ensureCsrfCookie();
  const { data, error, response } = await apiClient.POST(
    "/api/v1/chat/threads/{thread_id}/agent-runs",
    {
      params: { path: { thread_id: threadId } },
      body: { text: text.trim() },
    },
  );
  if (!data) {
    throw new ConversationsApiError(
      safeMessage(error, "The assistant is temporarily unavailable."),
      response.status,
    );
  }
  return data;
}

export async function deleteConversationThread(threadId: string): Promise<void> {
  await ensureCsrfCookie();
  const { error, response } = await apiClient.DELETE(
    "/api/v1/chat/threads/{thread_id}",
    { params: { path: { thread_id: threadId } } },
  );
  if (error) {
    throw new ConversationsApiError(
      safeMessage(error, "Unable to delete the conversation."),
      response.status,
    );
  }
}
