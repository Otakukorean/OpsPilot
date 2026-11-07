import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  deleteConversationThread,
  listConversationMessages,
  listConversationThreads,
  runConversationAgent,
} from "@/features/conversations/api";
import { MockOpsPilotApp } from "@/features/dashboard/mock-app";
import {
  deleteKnowledgeDocument,
  listKnowledgeDocuments,
  updateKnowledgeVisibility,
  uploadKnowledgeDocument,
} from "@/features/knowledge/api";
import { searchTickets } from "@/features/tickets/api";
import { queryTransactions } from "@/features/transactions/api";
import type { AuthUser } from "@/stores/auth-store";

vi.mock("@/features/tickets/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/tickets/api")>();
  return { ...original, searchTickets: vi.fn() };
});

vi.mock("@/features/transactions/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/transactions/api")>();
  return { ...original, queryTransactions: vi.fn() };
});

vi.mock("@/features/conversations/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/conversations/api")>();
  return {
    ...original,
    deleteConversationThread: vi.fn(),
    listConversationMessages: vi.fn(),
    listConversationThreads: vi.fn(),
    runConversationAgent: vi.fn(),
  };
});

vi.mock("@/features/knowledge/api", async (importOriginal) => {
  const original = await importOriginal<typeof import("@/features/knowledge/api")>();
  return {
    ...original,
    deleteKnowledgeDocument: vi.fn(),
    listKnowledgeDocuments: vi.fn(),
    updateKnowledgeVisibility: vi.fn(),
    uploadKnowledgeDocument: vi.fn(),
  };
});

const mockUser: AuthUser = {
  id: "4dd564fb-6c14-416b-ab06-d29dc7cbf9ea",
  email: "maya@example.test",
  first_name: "Maya",
  last_name: "Rahman",
  membership: {
    role: "analyst",
    workspace: {
      id: "ea242f16-60a2-41ed-b8e5-5731cbbb6fe6",
      name: "Northstar Demo",
    },
  },
};

const ticketPage = {
  items: [
    {
      id: "a53a40c4-94bd-491f-8670-405395241862",
      code: "TKT-2001",
      status: "open",
      public_detail: "Synthetic settlement review requested",
      created_at: "2026-11-07T08:30:00Z",
    },
  ],
  total: 1,
  limit: 10,
  offset: 0,
};

const transactionPage = {
  items: [
    {
      id: "beeaafce-3bfc-494e-a9f1-f0bce968cbfb",
      code: "TXN-9001",
      status: "failed",
      public_detail: "Synthetic settlement threshold exceeded",
      created_at: "2026-11-07T08:45:00Z",
    },
  ],
  total: 1,
  limit: 10,
  offset: 0,
};

const conversationThreadPage = {
  items: [
    {
      id: "4263d9c0-feb0-4cdc-9709-94724b927895",
      title: "Synthetic investigation",
      created_at: "2026-11-07T09:00:00Z",
      updated_at: "2026-11-07T09:05:00Z",
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
};

const conversationMessagePage = {
  items: [
    {
      id: "41340e08-a098-4849-8d7f-3217ac778902",
      role: "user" as const,
      body: "Review this synthetic transaction.",
      status: "stored" as const,
      created_at: "2026-11-07T09:05:00Z",
      citations: [],
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
};

const agentRun = {
  id: "9c2e99b9-0987-4395-8133-3037e464e109",
  status: "completed" as const,
  model: "synthetic-test-model",
  llm_calls: 2,
  tool_calls: 1,
  input_tokens: 30,
  output_tokens: 12,
  message: {
    id: "ddf0869b-0035-47ea-9268-0d641d306454",
    role: "assistant" as const,
    body: "The authorized synthetic evidence indicates a failed transaction.",
    status: "completed" as const,
    created_at: "2026-11-07T09:06:00Z",
    citations: [],
  },
  citations: [],
};

const knowledgeDocument = {
  id: "8451d851-cb12-4b15-94c5-f9a8552060ca",
  title: "Synthetic operations guide",
  original_filename: "synthetic-guide.txt",
  content_type: "text/plain",
  size_bytes: 28,
  sha256: "a".repeat(64),
  page_count: null,
  visibility: "viewer" as const,
  status: "ready" as const,
  failure_reason: "",
  version: 1,
  embedding_model: "local_hashing_v1",
  created_at: "2026-11-07T09:00:00Z",
  updated_at: "2026-11-07T09:05:00Z",
};

const knowledgeDocumentPage = {
  items: [knowledgeDocument],
  total: 1,
  limit: 50,
  offset: 0,
};

function TestProviders({ children }: Readonly<{ children: ReactNode }>) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

function renderApp(user: AuthUser = mockUser) {
  return render(
    <MockOpsPilotApp
      isLoggingOut={false}
      onLogout={vi.fn()}
      user={user}
    />,
    { wrapper: TestProviders },
  );
}

describe("MockOpsPilotApp", () => {
  beforeEach(() => {
    vi.mocked(searchTickets).mockReset();
    vi.mocked(searchTickets).mockResolvedValue(ticketPage);
    vi.mocked(queryTransactions).mockReset();
    vi.mocked(queryTransactions).mockResolvedValue(transactionPage);
    vi.mocked(listConversationThreads).mockReset();
    vi.mocked(listConversationThreads).mockResolvedValue(conversationThreadPage);
    vi.mocked(listConversationMessages).mockReset();
    vi.mocked(listConversationMessages).mockResolvedValue(conversationMessagePage);
    vi.mocked(deleteConversationThread).mockReset();
    vi.mocked(deleteConversationThread).mockResolvedValue();
    vi.mocked(runConversationAgent).mockReset();
    vi.mocked(runConversationAgent).mockResolvedValue(agentRun);
    vi.mocked(listKnowledgeDocuments).mockReset();
    vi.mocked(listKnowledgeDocuments).mockResolvedValue(knowledgeDocumentPage);
    vi.mocked(uploadKnowledgeDocument).mockReset();
    vi.mocked(uploadKnowledgeDocument).mockResolvedValue({
      ...knowledgeDocument,
      status: "queued",
      visibility: "restricted",
    });
    vi.mocked(updateKnowledgeVisibility).mockReset();
    vi.mocked(deleteKnowledgeDocument).mockReset();
  });

  it("shows the synthetic operations overview for the authenticated workspace", () => {
    renderApp();

    expect(screen.getByRole("heading", { name: "Good morning, Maya." })).toBeInTheDocument();
    expect(screen.getAllByText("Northstar Demo")).not.toHaveLength(0);
    expect(screen.getByText("Core workspace APIs live")).toBeInTheDocument();
    expect(screen.getByText("Ticket queue")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Notifications" })).not.toBeInTheDocument();
  });

  it("opens the server-assigned workspace menu", () => {
    renderApp();
    const workspaceSelector = screen.getByLabelText("Select workspace");
    const workspaceDetails = workspaceSelector.closest("details");

    expect(workspaceDetails).not.toHaveAttribute("open");
    fireEvent.click(workspaceSelector);

    expect(workspaceDetails).toHaveAttribute("open");
    expect(screen.getByText("This account has one server-assigned workspace.")).toBeInTheDocument();
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("routes global searches to the matching operations view", async () => {
    renderApp();
    const search = screen.getByRole("searchbox", { name: "Search tickets or transactions" });

    fireEvent.change(search, { target: { value: "settlement" } });
    expect(screen.getByRole("heading", { name: "Ticket queue" })).toBeInTheDocument();
    await waitFor(() => {
      expect(vi.mocked(searchTickets).mock.calls.some(([params]) =>
        params.query === "settlement",
      )).toBe(true);
    });

    fireEvent.change(search, { target: { value: "TXN-9001" } });
    expect(screen.getByRole("heading", { name: "Transactions" })).toBeInTheDocument();
    await waitFor(() => {
      expect(vi.mocked(queryTransactions).mock.calls.some(([params]) =>
        params.code === "TXN-9001",
      )).toBe(true);
    });
  });

  it("focuses global search with the command shortcut", () => {
    renderApp();
    const search = screen.getByRole("searchbox", { name: "Search tickets or transactions" });

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });

    expect(search).toHaveFocus();
  });

  it("navigates between live transactions and conversations", async () => {
    renderApp();

    const navigation = screen.getByRole("navigation", { name: "Main navigation" });

    fireEvent.click(within(navigation).getByRole("button", { name: "Transactions" }));
    expect(screen.getByRole("heading", { name: "Transactions" })).toBeInTheDocument();
    expect(await screen.findByText("TXN-9001")).toBeInTheDocument();

    fireEvent.click(within(navigation).getByRole("button", { name: "Conversations" }));
    expect(screen.getByRole("heading", { name: "Conversations" })).toBeInTheDocument();
    expect(await screen.findByText("Review this synthetic transaction.")).toBeInTheDocument();
    expect(screen.getByText("Owner-scoped conversation")).toBeInTheDocument();
  });

  it("loads and filters tickets through the real ticket query contract", async () => {
    renderApp();
    const navigation = screen.getByRole("navigation", { name: "Main navigation" });

    fireEvent.click(within(navigation).getByRole("button", { name: "Tickets" }));

    expect(await screen.findByText("TKT-2001")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open" }));

    await waitFor(() => {
      expect(vi.mocked(searchTickets).mock.calls.some(([params]) =>
        params.status === "open" && params.limit === 10,
      )).toBe(true);
    });
  });

  it("submits a conversation question through the agent endpoint", async () => {
    renderApp();
    const navigation = screen.getByRole("navigation", { name: "Main navigation" });
    fireEvent.click(within(navigation).getByRole("button", { name: "Conversations" }));
    await screen.findByText("Review this synthetic transaction.");

    fireEvent.change(screen.getByLabelText("Ask OpsPilot"), {
      target: { value: "Why did TXN-9001 fail?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Generate response" }));

    await waitFor(() => {
      expect(runConversationAgent).toHaveBeenCalledWith(
        conversationThreadPage.items[0].id,
        "Why did TXN-9001 fail?",
      );
    });
  });

  it("renders model output and citations as text instead of executable markup", async () => {
    const maliciousMarkup = "<img src=x onerror=alert('synthetic-xss')>";
    const maliciousCitation = "<script>window.syntheticAttack = true</script>";
    vi.mocked(listConversationMessages).mockResolvedValue({
      ...conversationMessagePage,
      items: [{
        ...conversationMessagePage.items[0],
        role: "assistant" as const,
        status: "completed" as const,
        body: maliciousMarkup,
        citations: [{
          source_number: 1,
          title: "Synthetic untrusted source",
          page: 1,
          excerpt: maliciousCitation,
        }],
      }],
    });
    renderApp();
    const navigation = screen.getByRole("navigation", { name: "Main navigation" });
    fireEvent.click(within(navigation).getByRole("button", { name: "Conversations" }));

    expect(await screen.findByText(maliciousMarkup)).toBeInTheDocument();
    expect(screen.getByText(maliciousCitation)).toBeInTheDocument();
    expect(document.querySelector("img[src='x']")).toBeNull();
    expect(document.querySelector("script")).toBeNull();
  });

  it("shows server-scoped knowledge while keeping management controls admin-only", async () => {
    renderApp();
    const navigation = screen.getByRole("navigation", { name: "Main navigation" });
    fireEvent.click(within(navigation).getByRole("button", { name: "Knowledge" }));

    expect(await screen.findByText("Synthetic operations guide")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Upload source" })).not.toBeInTheDocument();
    expect(screen.getByText("Admin access is required to manage sources.")).toBeInTheDocument();
  });

  it("lets an admin select and upload a synthetic TXT source", async () => {
    const adminUser: AuthUser = {
      ...mockUser,
      membership: mockUser.membership
        ? { ...mockUser.membership, role: "admin" }
        : null,
    };
    renderApp(adminUser);
    const navigation = screen.getByRole("navigation", { name: "Main navigation" });
    fireEvent.click(within(navigation).getByRole("button", { name: "Knowledge" }));
    await screen.findByText("Synthetic operations guide");

    fireEvent.click(screen.getByRole("button", { name: "Upload source" }));
    const uploadSection = screen.getByRole("heading", { name: "Upload a private source" }).closest("section");
    expect(uploadSection).not.toBeNull();
    const source = new File(["Synthetic knowledge"], "new-guide.txt", { type: "text/plain" });
    fireEvent.change(within(uploadSection!).getByLabelText("File"), {
      target: { files: [source] },
    });
    fireEvent.change(within(uploadSection!).getByLabelText(/Title/), {
      target: { value: "New synthetic guide" },
    });
    fireEvent.click(within(uploadSection!).getByRole("button", { name: "Upload source" }));

    await waitFor(() => {
      expect(uploadKnowledgeDocument).toHaveBeenCalledWith(source, "New synthetic guide");
    });
  });

  it("confirms knowledge deletion in the application modal", async () => {
    const adminUser: AuthUser = {
      ...mockUser,
      membership: mockUser.membership
        ? { ...mockUser.membership, role: "admin" }
        : null,
    };
    vi.mocked(deleteKnowledgeDocument).mockResolvedValue();
    renderApp(adminUser);
    const navigation = screen.getByRole("navigation", { name: "Main navigation" });
    fireEvent.click(within(navigation).getByRole("button", { name: "Knowledge" }));
    await screen.findByText("Synthetic operations guide");

    fireEvent.click(screen.getByRole("button", { name: "Delete Synthetic operations guide" }));

    const dialog = screen.getByRole("alertdialog", { name: "Delete knowledge source?" });
    expect(within(dialog).getByText("Synthetic operations guide")).toBeInTheDocument();
    expect(deleteKnowledgeDocument).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete source" }));

    await waitFor(() => {
      expect(vi.mocked(deleteKnowledgeDocument).mock.calls[0]?.[0]).toBe(knowledgeDocument.id);
    });
  });

  it("confirms conversation deletion in the application modal", async () => {
    renderApp();
    const navigation = screen.getByRole("navigation", { name: "Main navigation" });
    fireEvent.click(within(navigation).getByRole("button", { name: "Conversations" }));
    await screen.findByText("Review this synthetic transaction.");

    fireEvent.click(screen.getByRole("button", { name: "Delete conversation" }));

    const dialog = screen.getByRole("alertdialog", { name: "Delete conversation?" });
    expect(within(dialog).getByText("Synthetic investigation")).toBeInTheDocument();
    expect(screen.queryByText("Delete this conversation and all its messages?")).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete conversation" }));

    await waitFor(() => {
      expect(vi.mocked(deleteConversationThread).mock.calls[0]?.[0]).toBe(conversationThreadPage.items[0].id);
    });
  });
});
