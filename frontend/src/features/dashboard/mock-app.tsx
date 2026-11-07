"use client";

import {
  Activity,
  ArrowRight,
  BookOpenText,
  Bot,
  Check,
  ChevronDown,
  CircleAlert,
  CircleDot,
  Clock3,
  Command,
  FileText,
  Gauge,
  Inbox,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  Menu,
  MessageSquareText,
  Plus,
  Search,
  Send,
  Sparkles,
  TicketCheck,
  Trash2,
  WalletCards,
  X,
} from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";

import { ConfirmationModal } from "@/components/confirmation-modal";
import {
  mockActivity,
} from "@/features/dashboard/mock-data";
import {
  createConversationThread,
  deleteConversationThread,
  type ConversationThread,
  type ConversationThreadPage,
  runConversationAgent,
} from "@/features/conversations/api";
import {
  conversationKeys,
  useConversationMessages,
  useConversationThreads,
} from "@/features/conversations/queries";
import {
  deleteKnowledgeDocument,
  type KnowledgeDocument,
  type KnowledgeDocumentPage,
  type KnowledgeVisibility,
  updateKnowledgeVisibility,
  uploadKnowledgeDocument,
} from "@/features/knowledge/api";
import {
  knowledgeKeys,
  useKnowledgeDocuments,
} from "@/features/knowledge/queries";
import { type Ticket, TicketsApiError } from "@/features/tickets/api";
import { useTickets } from "@/features/tickets/queries";
import { type Transaction, TransactionsApiError } from "@/features/transactions/api";
import { useTransactions } from "@/features/transactions/queries";
import { cn } from "@/lib/cn";
import type { AuthUser } from "@/stores/auth-store";

type View = "overview" | "tickets" | "transactions" | "conversations" | "knowledge";

type MockOpsPilotAppProps = {
  user: AuthUser;
  isLoggingOut: boolean;
  logoutError?: string;
  onLogout: () => void;
};

const navItems: Array<{ id: View; label: string; icon: typeof LayoutDashboard }> = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "tickets", label: "Tickets", icon: TicketCheck },
  { id: "transactions", label: "Transactions", icon: WalletCards },
  { id: "conversations", label: "Conversations", icon: MessageSquareText },
  { id: "knowledge", label: "Knowledge", icon: BookOpenText },
];

const viewTitles: Record<View, { eyebrow: string; title: string; description: string }> = {
  overview: { eyebrow: "Operations desk", title: "Good morning", description: "Here is the synthetic workspace pulse for today." },
  tickets: { eyebrow: "Operations", title: "Ticket queue", description: "Triage and track synthetic support requests." },
  transactions: { eyebrow: "Operations", title: "Transactions", description: "Monitor the latest synthetic transaction activity." },
  conversations: { eyebrow: "Workspace conversations", title: "Conversations", description: "Manage your owner-scoped workspace conversations." },
  knowledge: { eyebrow: "Workspace sources", title: "Knowledge base", description: "Manage the synthetic sources available to OpsPilot." },
};

function TicketBadge({ status }: { status: string }) {
  const labels: Record<string, string> = { open: "Open", in_progress: "In progress", resolved: "Resolved" };
  return <span className={cn("inline-flex items-center gap-1.5 text-xs font-semibold", status === "open" && "text-[#a54838]", status === "in_progress" && "text-[#926918]", status === "resolved" && "text-[#277056]")}><span className="size-1.5 rounded-full bg-current" />{labels[status] ?? status}</span>;
}

function TransactionBadge({ status }: { status: string }) {
  return <span className={cn("inline-flex min-w-[74px] items-center justify-center border px-2 py-1 text-[11px] font-bold capitalize", status === "completed" && "border-[#b8d7c9] bg-[#eaf4ef] text-[#216248]", status === "pending" && "border-[#e2d2ab] bg-[#faf4e5] text-[#876016]", status === "failed" && "border-[#e4c0ba] bg-[#faece9] text-[#963e33]")}>{status}</span>;
}

function MiniPulse() {
  return (
    <svg aria-hidden="true" className="h-8 w-24" viewBox="0 0 96 32">
      <path d="M1 23 L13 23 L20 17 L27 25 L36 7 L44 19 L52 15 L61 21 L70 11 L78 17 L95 8" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
    </svg>
  );
}

function OverviewView({ setView }: { setView: (view: View) => void }) {
  const recentTickets = useTickets({ limit: 4, offset: 0 });
  const openTickets = useTickets({ limit: 1, offset: 0, status: "open" });
  const recentTransactions = useTransactions({ limit: 4, offset: 0 });
  const failedTransactions = useTransactions({ limit: 1, offset: 0, status: "failed" });

  return (
    <div className="space-y-5">
      <section aria-label="Operational pulse" className="grid border border-[#d4d9d1] bg-[#fbfcf8] shadow-[0_10px_32px_rgba(23,32,29,0.055)] sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Open tickets", value: openTickets.data ? String(openTickets.data.total) : "—", note: openTickets.isError ? "Unable to load" : "Live workspace total", icon: Inbox, tone: "text-[#a54838]", action: "tickets" as View },
          { label: "Failed transactions", value: failedTransactions.data ? String(failedTransactions.data.total) : "—", note: failedTransactions.isError ? "Unable to load" : "Live workspace total", icon: CircleAlert, tone: "text-[#a54838]", action: "transactions" as View },
          { label: "Knowledge ready", value: "98%", note: "142 sources indexed", icon: BookOpenText, tone: "text-[#176b50]", action: "knowledge" as View },
          { label: "Agent response", value: "1.4s", note: "Within target", icon: Gauge, tone: "text-[#176b50]", action: "conversations" as View },
        ].map((metric, index) => (
          <button key={metric.label} className={cn("group flex min-h-32 items-start gap-4 p-5 text-left transition-colors hover:bg-[#f3f6f0]", index > 0 && "border-t border-[#e0e4dd] sm:border-l sm:border-t-0", index === 2 && "sm:border-l-0 xl:border-l", index === 3 && "sm:border-l")} onClick={() => setView(metric.action)} type="button">
            <div className={cn("mt-0.5 flex size-9 shrink-0 items-center justify-center border border-[#d7dcd5] bg-white", metric.tone)}><metric.icon aria-hidden="true" size={18} /></div>
            <div className="min-w-0 flex-1"><p className="text-xs font-semibold text-[#68736f]">{metric.label}</p><div className="mt-2 flex items-end justify-between gap-2"><p className="text-3xl font-semibold tracking-[-0.05em] text-[#17201d]">{metric.value}</p><span className={cn("opacity-65 transition-opacity group-hover:opacity-100", metric.tone)}><MiniPulse /></span></div><p className="mt-1 text-xs text-[#7a8580]">{metric.note}</p></div>
          </button>
        ))}
      </section>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(310px,0.65fr)]">
        <section className="border border-[#d4d9d1] bg-[#fbfcf8] shadow-[0_10px_32px_rgba(23,32,29,0.045)]">
          <PanelHeader title="Ticket queue" note="Live workspace tickets" action="View all" onAction={() => setView("tickets")} />
          <div className="overflow-x-auto">
            <table className="w-full min-w-[610px] border-collapse text-left">
              <thead><tr className="border-y border-[#e1e4de] bg-[#f5f6f2] text-[11px] font-bold uppercase tracking-[0.1em] text-[#78827e]"><th className="px-5 py-3">Ticket</th><th className="px-3 py-3">Status</th><th className="px-5 py-3 text-right">Created</th></tr></thead>
              <tbody className="divide-y divide-[#e5e7e2]">{recentTickets.data?.items.map((ticket) => <TicketRow key={ticket.id} ticket={ticket} />)}</tbody>
            </table>
            {recentTickets.isPending ? <TicketTableLoading compact /> : null}
            {recentTickets.isError ? <TicketError compact error={recentTickets.error} onRetry={() => void recentTickets.refetch()} /> : null}
            {recentTickets.data?.items.length === 0 ? <TicketEmpty compact /> : null}
          </div>
        </section>

        <section className="border border-[#164e3d] bg-[#173f34] p-5 text-[#f4f7f3] shadow-[0_16px_38px_rgba(15,55,44,0.18)] sm:p-6">
          <div className="flex items-center justify-between"><div className="flex size-9 items-center justify-center border border-white/20 bg-white/10"><Sparkles aria-hidden="true" size={18} /></div><span className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-emerald-100/75"><span className="size-1.5 rounded-full bg-[#75d5ad]" />Agent ready</span></div>
          <h2 className="mt-7 text-2xl font-semibold tracking-[-0.035em]">Ask the operation.</h2>
          <p className="mt-2 text-sm leading-6 text-emerald-50/70">Get an evidence-backed answer across synthetic tickets, transactions, and workspace knowledge.</p>
          <div className="mt-6 space-y-2">{["Why did TXN-88431 fail?", "Summarize open settlement tickets", "What is the escalation process?"].map((prompt) => <button key={prompt} className="group flex w-full items-center justify-between border border-white/15 bg-white/[0.06] px-3.5 py-3 text-left text-sm transition-colors hover:bg-white/10" onClick={() => setView("conversations")} type="button"><span>{prompt}</span><ArrowRight aria-hidden="true" className="shrink-0 opacity-60 transition-transform group-hover:translate-x-0.5" size={16} /></button>)}</div>
          <button className="mt-5 flex h-11 w-full items-center justify-center gap-2 bg-[#f4f7f3] text-sm font-bold text-[#173f34] transition-colors hover:bg-white" onClick={() => setView("conversations")} type="button"><MessageSquareText aria-hidden="true" size={17} />Start conversation</button>
        </section>
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(290px,0.65fr)]">
        <section className="border border-[#d4d9d1] bg-[#fbfcf8]">
          <PanelHeader title="Recent transactions" note="Live workspace transactions" action="View all" onAction={() => setView("transactions")} />
          <div className="divide-y divide-[#e4e7e1]">{recentTransactions.data?.items.map((transaction) => <TransactionLine key={transaction.id} transaction={transaction} />)}</div>
          {recentTransactions.isPending ? <TransactionListLoading compact /> : null}
          {recentTransactions.isError ? <TransactionError compact error={recentTransactions.error} onRetry={() => void recentTransactions.refetch()} /> : null}
          {recentTransactions.data?.items.length === 0 ? <TransactionEmpty compact /> : null}
        </section>
        <section className="border border-[#d4d9d1] bg-[#fbfcf8]">
          <PanelHeader title="Activity" note="Workspace updates" />
          <ol className="px-5 pb-5">{mockActivity.map((item, index) => <li key={item.label} className="relative grid grid-cols-[18px_1fr] gap-3 pb-5 last:pb-0"><span className={cn("relative z-10 mt-1.5 size-2 rounded-full ring-4 ring-[#fbfcf8]", item.tone === "red" ? "bg-[#b24b3d]" : item.tone === "blue" ? "bg-[#477d9f]" : "bg-[#2d8060]")} />{index < mockActivity.length - 1 ? <span aria-hidden="true" className="absolute left-[3.5px] top-3 h-full w-px bg-[#dce1da]" /> : null}<div><p className="text-sm font-medium text-[#2b3531]">{item.label}</p><p className="mt-1 text-xs text-[#818b87]">{item.time}</p></div></li>)}</ol>
        </section>
      </div>
    </div>
  );
}

function PanelHeader({ title, note, action, onAction }: { title: string; note: string; action?: string; onAction?: () => void }) {
  return <header className="flex items-start justify-between gap-4 px-5 py-4"><div><h2 className="font-semibold tracking-[-0.015em] text-[#24302b]">{title}</h2><p className="mt-0.5 text-xs text-[#7b8581]">{note}</p></div>{action ? <button className="flex items-center gap-1 text-xs font-bold text-[#176b50] hover:text-[#0f533d]" onClick={onAction} type="button">{action}<ArrowRight aria-hidden="true" size={14} /></button> : null}</header>;
}

function formatRecordDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Unknown";
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "UTC" }).format(date);
}

function formatFileSize(bytes: number) {
  if (bytes < 1_024) return `${bytes} B`;
  if (bytes < 1_048_576) return `${(bytes / 1_024).toFixed(1)} KB`;
  return `${(bytes / 1_048_576).toFixed(1)} MB`;
}

function TicketRow({ ticket }: { ticket: Ticket }) {
  return <tr className="group transition-colors hover:bg-[#f5f7f3]"><td className="px-5 py-3.5"><p className="font-mono text-xs font-bold text-[#245e4b]">{ticket.code}</p><p className="mt-1 max-w-xl truncate text-sm text-[#4f5b56]">{ticket.public_detail}</p></td><td className="px-3 py-3.5"><TicketBadge status={ticket.status} /></td><td className="px-5 py-3.5 text-right font-mono text-xs text-[#77827d]">{formatRecordDate(ticket.created_at)} UTC</td></tr>;
}

function TicketTableLoading({ compact = false }: { compact?: boolean }) {
  return <div aria-label="Loading tickets" className={cn("space-y-3 p-5", compact ? "min-h-40" : "min-h-56")} role="status">{Array.from({ length: compact ? 3 : 5 }).map((_, index) => <div key={index} className="h-11 animate-pulse bg-[#edf0eb]" />)}</div>;
}

function TicketError({ error, onRetry, compact = false }: { error: Error; onRetry: () => void; compact?: boolean }) {
  const denied = error instanceof TicketsApiError && error.status === 403;
  return <div className={cn("grid place-items-center px-6 text-center", compact ? "min-h-40" : "min-h-64")} role="alert"><div><CircleAlert aria-hidden="true" className="mx-auto text-[#a54838]" size={22} /><p className="mt-3 text-sm font-semibold">{denied ? "Tickets are unavailable for your role" : "Tickets could not be loaded"}</p><p className="mt-1 text-xs text-[#74807a]">{denied ? "Ask a workspace Admin for Analyst access." : "Check your connection and try again."}</p>{!denied ? <button className="mt-4 border border-[#b9c4bc] bg-white px-3 py-2 text-xs font-bold text-[#195a43]" onClick={onRetry} type="button">Retry</button> : null}</div></div>;
}

function TicketEmpty({ compact = false }: { compact?: boolean }) {
  return <div className={cn("grid place-items-center p-6 text-center", compact ? "min-h-40" : "min-h-64")}><div><TicketCheck aria-hidden="true" className="mx-auto text-[#73817a]" size={22} /><p className="mt-3 text-sm font-semibold">No tickets found</p><p className="mt-1 text-xs text-[#7c8782]">Try a different search or status.</p></div></div>;
}

function TransactionLine({ transaction }: { transaction: Transaction }) {
  return <div className="grid grid-cols-[1fr_auto] items-center gap-4 px-5 py-3.5 transition-colors hover:bg-[#f5f7f3] sm:grid-cols-[120px_1fr_auto_auto]"><div><p className="font-mono text-xs font-bold text-[#245e4b]">{transaction.code}</p><p className="mt-1 text-xs text-[#85908b] sm:hidden">{transaction.public_detail}</p></div><p className="hidden truncate text-sm text-[#59645f] sm:block">{transaction.public_detail}</p><p className="hidden font-mono text-xs text-[#77827d] sm:block">{formatRecordDate(transaction.created_at)} UTC</p><TransactionBadge status={transaction.status} /></div>;
}

function TransactionListLoading({ compact = false }: { compact?: boolean }) {
  return <div aria-label="Loading transactions" className={cn("space-y-3 p-5", compact ? "min-h-40" : "min-h-56")} role="status">{Array.from({ length: compact ? 3 : 5 }).map((_, index) => <div key={index} className="h-11 animate-pulse bg-[#edf0eb]" />)}</div>;
}

function TransactionError({ error, onRetry, compact = false }: { error: Error; onRetry: () => void; compact?: boolean }) {
  const denied = error instanceof TransactionsApiError && error.status === 403;
  return <div className={cn("grid place-items-center px-6 text-center", compact ? "min-h-40" : "min-h-64")} role="alert"><div><CircleAlert aria-hidden="true" className="mx-auto text-[#a54838]" size={22} /><p className="mt-3 text-sm font-semibold">{denied ? "Transactions are unavailable for your role" : "Transactions could not be loaded"}</p><p className="mt-1 text-xs text-[#74807a]">{denied ? "Ask a workspace Admin for Analyst access." : "Check your connection and try again."}</p>{!denied ? <button className="mt-4 border border-[#b9c4bc] bg-white px-3 py-2 text-xs font-bold text-[#195a43]" onClick={onRetry} type="button">Retry</button> : null}</div></div>;
}

function TransactionEmpty({ compact = false }: { compact?: boolean }) {
  return <div className={cn("grid place-items-center p-6 text-center", compact ? "min-h-40" : "min-h-64")}><div><WalletCards aria-hidden="true" className="mx-auto text-[#73817a]" size={22} /><p className="mt-3 text-sm font-semibold">No transactions found</p><p className="mt-1 text-xs text-[#7c8782]">Try an exact reference or a different status.</p></div></div>;
}

function TicketsView({ search }: { search: string }) {
  const deferredSearch = useDeferredValue(search.trim());
  const [status, setStatus] = useState<"all" | "open" | "in_progress" | "resolved">("all");
  const [pagination, setPagination] = useState({ offset: 0, query: "" });
  const limit = 10;
  const offset = pagination.query === deferredSearch ? pagination.offset : 0;
  const tickets = useTickets({ query: deferredSearch || undefined, status: status === "all" ? undefined : status, limit, offset });

  const total = tickets.data?.total ?? 0;
  const start = total === 0 ? 0 : offset + 1;
  const end = Math.min(offset + limit, total);
  const filters = [{ id: "all", label: "All" }, { id: "open", label: "Open" }, { id: "in_progress", label: "In progress" }, { id: "resolved", label: "Resolved" }] as const;

  return <section className="border border-[#d4d9d1] bg-[#fbfcf8]"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e0e4dd] px-5 py-4"><div className="flex flex-wrap gap-2">{filters.map((filter) => <button key={filter.id} aria-pressed={status === filter.id} className={cn("border px-3 py-2 text-xs font-semibold", status === filter.id ? "border-[#b9c4bc] bg-[#edf4ef] font-bold text-[#195a43]" : "border-[#d7dcd5] bg-white text-[#69746f]")} onClick={() => { setStatus(filter.id); setPagination({ offset: 0, query: deferredSearch }); }} type="button">{filter.label}{filter.id === "all" && tickets.data ? ` ${tickets.data.total}` : ""}</button>)}</div><span className="flex items-center gap-1.5 text-xs font-bold text-[#58645e]">Newest first{tickets.isFetching ? <LoaderCircle aria-hidden="true" className="animate-spin" size={13} /> : <ChevronDown aria-hidden="true" size={14} />}</span></div><div className="overflow-x-auto">{tickets.isPending ? <TicketTableLoading /> : tickets.isError ? <TicketError error={tickets.error} onRetry={() => void tickets.refetch()} /> : tickets.data?.items.length === 0 ? <TicketEmpty /> : <table className="w-full min-w-[640px] text-left"><thead><tr className="border-b border-[#e1e4de] bg-[#f5f6f2] text-[11px] font-bold uppercase tracking-[0.1em] text-[#78827e]"><th className="px-5 py-3">Ticket</th><th className="px-3 py-3">Status</th><th className="px-5 py-3 text-right">Created</th></tr></thead><tbody className="divide-y divide-[#e5e7e2]">{tickets.data?.items.map((ticket) => <TicketRow key={ticket.id} ticket={ticket} />)}</tbody></table>}</div>{tickets.data && tickets.data.total > 0 ? <footer className="flex items-center justify-between border-t border-[#e0e4dd] px-5 py-3"><p className="text-xs text-[#74807a]">Showing {start}–{end} of {total}</p><div className="flex gap-2"><button className="border border-[#d2d8d1] bg-white px-3 py-1.5 text-xs font-semibold disabled:opacity-40" disabled={offset === 0 || tickets.isFetching} onClick={() => setPagination({ offset: Math.max(0, offset - limit), query: deferredSearch })} type="button">Previous</button><button className="border border-[#d2d8d1] bg-white px-3 py-1.5 text-xs font-semibold disabled:opacity-40" disabled={offset + limit >= total || tickets.isFetching} onClick={() => setPagination({ offset: offset + limit, query: deferredSearch })} type="button">Next</button></div></footer> : null}</section>;
}

function TransactionsView({ search }: { search: string }) {
  const deferredCode = useDeferredValue(search.trim());
  const [status, setStatus] = useState<"all" | "pending" | "completed" | "failed">("all");
  const [pagination, setPagination] = useState({ offset: 0, code: "" });
  const limit = 10;
  const offset = pagination.code === deferredCode ? pagination.offset : 0;
  const transactions = useTransactions({ code: deferredCode || undefined, status: status === "all" ? undefined : status, limit, offset });
  const allCount = useTransactions({ limit: 1, offset: 0 });
  const pendingCount = useTransactions({ limit: 1, offset: 0, status: "pending" });
  const failedCount = useTransactions({ limit: 1, offset: 0, status: "failed" });
  const total = transactions.data?.total ?? 0;
  const start = total === 0 ? 0 : offset + 1;
  const end = Math.min(offset + limit, total);
  const filters = [{ id: "all", label: "All" }, { id: "pending", label: "Pending" }, { id: "completed", label: "Completed" }, { id: "failed", label: "Failed" }] as const;

  return <section className="border border-[#d4d9d1] bg-[#fbfcf8]"><div className="grid gap-3 border-b border-[#e0e4dd] p-5 sm:grid-cols-3"><div className="border-l-2 border-[#176b50] pl-3"><p className="text-xs text-[#77827d]">Total transactions</p><p className="mt-1 text-xl font-semibold">{allCount.data?.total ?? "—"}</p></div><div className="border-l-2 border-[#b37a19] pl-3"><p className="text-xs text-[#77827d]">Pending</p><p className="mt-1 text-xl font-semibold">{pendingCount.data?.total ?? "—"}</p></div><div className="border-l-2 border-[#ad493b] pl-3"><p className="text-xs text-[#77827d]">Failed</p><p className="mt-1 text-xl font-semibold">{failedCount.data?.total ?? "—"}</p></div></div><div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e0e4dd] px-5 py-4"><div className="flex flex-wrap gap-2">{filters.map((filter) => <button key={filter.id} aria-pressed={status === filter.id} className={cn("border px-3 py-2 text-xs font-semibold", status === filter.id ? "border-[#b9c4bc] bg-[#edf4ef] font-bold text-[#195a43]" : "border-[#d7dcd5] bg-white text-[#69746f]")} onClick={() => { setStatus(filter.id); setPagination({ offset: 0, code: deferredCode }); }} type="button">{filter.label}</button>)}</div><span className="flex items-center gap-1.5 text-xs text-[#6d7873]">Reference search is exact{transactions.isFetching ? <LoaderCircle aria-hidden="true" className="animate-spin" size={13} /> : null}</span></div>{transactions.isPending ? <TransactionListLoading /> : transactions.isError ? <TransactionError error={transactions.error} onRetry={() => void transactions.refetch()} /> : transactions.data?.items.length === 0 ? <TransactionEmpty /> : <div className="divide-y divide-[#e4e7e1]">{transactions.data?.items.map((transaction) => <TransactionLine key={transaction.id} transaction={transaction} />)}</div>}{transactions.data && transactions.data.total > 0 ? <footer className="flex items-center justify-between border-t border-[#e0e4dd] px-5 py-3"><p className="text-xs text-[#74807a]">Showing {start}–{end} of {total}</p><div className="flex gap-2"><button className="border border-[#d2d8d1] bg-white px-3 py-1.5 text-xs font-semibold disabled:opacity-40" disabled={offset === 0 || transactions.isFetching} onClick={() => setPagination({ offset: Math.max(0, offset - limit), code: deferredCode })} type="button">Previous</button><button className="border border-[#d2d8d1] bg-white px-3 py-1.5 text-xs font-semibold disabled:opacity-40" disabled={offset + limit >= total || transactions.isFetching} onClick={() => setPagination({ offset: offset + limit, code: deferredCode })} type="button">Next</button></div></footer> : null}</section>;
}

function ConversationsView() {
  const queryClient = useQueryClient();
  const [selectedThreadId, setSelectedThreadId] = useState<string>();
  const [draft, setDraft] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [pendingQuestion, setPendingQuestion] = useState<{ threadId: string; text: string }>();
  const [threadToDelete, setThreadToDelete] = useState<ConversationThread>();
  const threads = useConversationThreads();
  const activeThreadId = selectedThreadId ?? threads.data?.items[0]?.id;
  const activeThread = threads.data?.items.find((thread) => thread.id === activeThreadId);
  const activePendingQuestion = pendingQuestion?.threadId === activeThreadId
    ? pendingQuestion
    : undefined;
  const messages = useConversationMessages(activeThreadId);

  const createThread = useMutation({
    mutationFn: createConversationThread,
    onSuccess(thread) {
      setSelectedThreadId(thread.id);
      setNewTitle("");
      setShowCreateForm(false);
      queryClient.setQueryData<ConversationThreadPage>(
        conversationKeys.threads,
        (current) => current
          ? { ...current, items: [thread, ...current.items], total: current.total + 1 }
          : { items: [thread], total: 1, limit: 50, offset: 0 },
      );
      void queryClient.invalidateQueries({ queryKey: conversationKeys.threads });
    },
  });

  const runAgent = useMutation({
    mutationFn: ({ threadId, text }: { threadId: string; text: string }) =>
      runConversationAgent(threadId, text),
    onMutate(variables) {
      const question = variables.text.trim();
      setPendingQuestion({ threadId: variables.threadId, text: question });
      setDraft("");
    },
    async onSuccess(_, variables) {
      await queryClient.invalidateQueries({
        queryKey: conversationKeys.messages(variables.threadId),
      });
      setPendingQuestion(undefined);
      void queryClient.invalidateQueries({ queryKey: conversationKeys.threads });
    },
    async onError(_, variables) {
      await queryClient.invalidateQueries({
        queryKey: conversationKeys.messages(variables.threadId),
      });
      setPendingQuestion(undefined);
    },
  });

  const deleteThread = useMutation({
    mutationFn: deleteConversationThread,
    onSuccess(_, threadId) {
      setThreadToDelete(undefined);
      setSelectedThreadId(undefined);
      queryClient.setQueryData<ConversationThreadPage>(
        conversationKeys.threads,
        (current) => current
          ? {
              ...current,
              items: current.items.filter((thread) => thread.id !== threadId),
              total: Math.max(0, current.total - 1),
            }
          : current,
      );
      queryClient.removeQueries({ queryKey: conversationKeys.messages(threadId) });
      void queryClient.invalidateQueries({ queryKey: conversationKeys.threads });
    },
  });

  return (
    <section className="grid min-h-[620px] overflow-hidden border border-[#d4d9d1] bg-[#fbfcf8] lg:grid-cols-[280px_1fr]">
      <aside className="max-h-72 overflow-y-auto border-b border-[#dfe3dc] bg-[#f5f6f2] lg:max-h-none lg:border-b-0 lg:border-r">
        <div className="sticky top-0 z-10 border-b border-[#dfe3dc] bg-[#f5f6f2] p-4">
          {showCreateForm ? (
            <form
              className="space-y-2"
              onSubmit={(event) => {
                event.preventDefault();
                if (newTitle.trim()) createThread.mutate(newTitle);
              }}
            >
              <label className="text-xs font-bold text-[#39443f]" htmlFor="conversation-title">Conversation title</label>
              <input autoFocus className="h-10 w-full border border-[#c9d1ca] bg-white px-3 text-sm outline-none focus:border-[#176b50]" id="conversation-title" maxLength={120} onChange={(event) => setNewTitle(event.target.value)} placeholder="Synthetic investigation" value={newTitle} />
              <div className="flex gap-2"><button className="h-9 flex-1 bg-[#176b50] text-xs font-bold text-white disabled:opacity-60" disabled={!newTitle.trim() || createThread.isPending} type="submit">{createThread.isPending ? "Creating…" : "Create"}</button><button className="h-9 border border-[#ced5ce] bg-white px-3 text-xs font-semibold" onClick={() => setShowCreateForm(false)} type="button">Cancel</button></div>
              {createThread.isError ? <p className="text-xs text-[#a33b32]" role="alert">{createThread.error.message}</p> : null}
            </form>
          ) : (
            <button className="flex h-10 w-full items-center justify-center gap-2 bg-[#176b50] text-sm font-bold text-white" onClick={() => setShowCreateForm(true)} type="button"><Plus aria-hidden="true" size={16} />New conversation</button>
          )}
        </div>
        {threads.isPending ? <p className="p-4 text-xs text-[#74807a]" role="status">Loading conversations…</p> : null}
        {threads.isError ? <div className="p-4 text-xs text-[#9b4336]" role="alert"><p>Could not load conversations.</p><button className="mt-2 font-bold underline" onClick={() => void threads.refetch()} type="button">Retry</button></div> : null}
        {threads.data?.items.length === 0 ? <p className="p-5 text-center text-xs leading-5 text-[#74807a]">No conversations yet. Create one to store your first message.</p> : null}
        <div className="divide-y divide-[#dfe3dc]">{threads.data?.items.map((thread) => <button key={thread.id} className={cn("w-full px-4 py-4 text-left transition-colors hover:bg-white", activeThreadId === thread.id && "bg-white shadow-[inset_2px_0_0_#176b50]")} onClick={() => setSelectedThreadId(thread.id)} type="button"><p className="truncate text-sm font-semibold text-[#29342f]">{thread.title}</p><p className="mt-1 text-[10px] text-[#89928e]">Updated {formatRecordDate(thread.updated_at)} UTC</p></button>)}</div>
      </aside>

      <div className="flex min-w-0 flex-col">
        {activeThread ? (
          <>
            <header className="flex min-h-16 items-center justify-between gap-4 border-b border-[#dfe3dc] px-5 py-3"><div><h2 className="text-sm font-semibold">{activeThread.title}</h2><p className="mt-0.5 flex items-center gap-1 text-[11px] text-[#74807a]"><Check aria-hidden="true" size={12} />Owner-scoped conversation</p></div><button aria-label="Delete conversation" className="flex size-9 items-center justify-center text-[#7d8883] hover:bg-[#faece9] hover:text-[#a33b32] disabled:opacity-50" disabled={deleteThread.isPending || runAgent.isPending} onClick={() => { deleteThread.reset(); setThreadToDelete(activeThread); }} type="button"><Trash2 aria-hidden="true" size={17} /></button></header>
            <div className="flex-1 space-y-5 overflow-y-auto p-5 sm:p-8">
              {messages.isPending ? <p className="text-sm text-[#74807a]" role="status">Loading messages…</p> : null}
              {messages.isError ? <div className="text-sm text-[#9b4336]" role="alert">Could not load messages. <button className="font-bold underline" onClick={() => void messages.refetch()} type="button">Retry</button></div> : null}
              {messages.data?.items.length === 0 && !activePendingQuestion ? <div className="grid min-h-64 place-items-center text-center"><div><MessageSquareText aria-hidden="true" className="mx-auto text-[#71817a]" size={24} /><p className="mt-3 text-sm font-semibold">Start the conversation</p><p className="mt-1 text-xs text-[#7b8681]">Messages are stored securely in this workspace.</p></div></div> : null}
              {messages.data?.items.map((message) => message.role === "user" ? <div key={message.id} className="ml-auto max-w-[82%]"><div className="whitespace-pre-wrap bg-[#1a4e3e] px-4 py-3 text-sm leading-6 text-white">{message.body}</div><p className="mt-1 text-right text-[10px] text-[#87918d]">Stored · {formatRecordDate(message.created_at)} UTC</p></div> : <div key={message.id} className="max-w-[88%]"><div className="mb-2 flex items-center gap-2 text-xs font-bold text-[#245e4b]"><span className="flex size-7 items-center justify-center border border-[#c5d0c8] bg-white"><Bot aria-hidden="true" size={15} /></span>OpsPilot</div><div className="whitespace-pre-wrap border border-[#d9ded7] bg-white p-4 text-sm leading-6 text-[#3e4a45] shadow-sm">{message.body}</div>{message.citations.length > 0 ? <div className="mt-2 space-y-2" aria-label="Response sources"><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#65716c]">Sources</p>{message.citations.map((citation) => <div key={`${message.id}-${citation.source_number}`} className="border-l-2 border-[#8eb5a5] bg-[#f2f6f2] px-3 py-2 text-xs text-[#5f6c66]"><p className="font-bold text-[#315c4d]">[{citation.source_number}] {citation.title}{citation.page ? ` · Page ${citation.page}` : ""}</p><p className="mt-1 line-clamp-2 leading-5">{citation.excerpt}</p></div>)}</div> : null}</div>)}
              {activePendingQuestion ? <div className="ml-auto max-w-[82%] opacity-75"><div className="whitespace-pre-wrap bg-[#1a4e3e] px-4 py-3 text-sm leading-6 text-white">{activePendingQuestion.text}</div><p className="mt-1 text-right text-[10px] text-[#87918d]">Sending…</p></div> : null}
              {runAgent.isPending && activePendingQuestion ? <div className="max-w-[88%]" role="status"><div className="mb-2 flex items-center gap-2 text-xs font-bold text-[#245e4b]"><span className="flex size-7 items-center justify-center border border-[#c5d0c8] bg-white"><LoaderCircle aria-hidden="true" className="animate-spin" size={15} /></span>OpsPilot is checking authorized evidence…</div><div className="h-16 animate-pulse border border-[#d9ded7] bg-white shadow-sm" /></div> : null}
            </div>
            <div className="border-t border-[#e0e4dd] bg-[#f8f9f5] px-4 py-3 text-center text-[11px] text-[#76827c]">OpsPilot can use only server-authorized, read-only workspace evidence.</div>
            <form className="m-4 mt-3 flex items-end gap-2 border border-[#c8d0c9] bg-white p-2 shadow-[0_8px_24px_rgba(23,32,29,0.08)] sm:m-6 sm:mt-3" onSubmit={(event) => { event.preventDefault(); if (activeThreadId && draft.trim() && !runAgent.isPending) runAgent.mutate({ threadId: activeThreadId, text: draft }); }}><label className="sr-only" htmlFor="conversation-message">Ask OpsPilot</label><textarea className="min-h-11 flex-1 resize-none px-2 py-2.5 text-sm outline-none placeholder:text-[#919a96] disabled:bg-white disabled:opacity-60" disabled={runAgent.isPending} id="conversation-message" maxLength={4000} onChange={(event) => setDraft(event.target.value)} placeholder="Ask about a synthetic transaction, ticket, or knowledge source…" rows={1} value={draft} /><button aria-label="Generate response" className="flex size-10 shrink-0 items-center justify-center bg-[#176b50] text-white disabled:bg-[#9aaba4]" disabled={!draft.trim() || runAgent.isPending} type="submit">{runAgent.isPending ? <LoaderCircle aria-hidden="true" className="animate-spin" size={17} /> : <Send aria-hidden="true" size={17} />}</button></form>
            {runAgent.isError ? <p className="mx-6 mb-4 text-xs text-[#a33b32]" role="alert">{runAgent.error.message} Your question remains in the conversation history.</p> : null}
            {deleteThread.isError && !threadToDelete ? <p className="mx-6 mb-4 text-xs text-[#a33b32]" role="alert">{deleteThread.error.message}</p> : null}
          </>
        ) : (
          <div className="grid flex-1 place-items-center p-8 text-center"><div><MessageSquareText aria-hidden="true" className="mx-auto text-[#71817a]" size={28} /><h2 className="mt-4 font-semibold">No conversation selected</h2><p className="mt-1 text-sm text-[#77827d]">Create a conversation to begin.</p></div></div>
        )}
      </div>
      <ConfirmationModal
        confirmLabel="Delete conversation"
        description="Delete this conversation and every message and citation stored inside it."
        error={deleteThread.isError ? deleteThread.error.message : undefined}
        isPending={deleteThread.isPending}
        onCancel={() => { if (!deleteThread.isPending) { setThreadToDelete(undefined); deleteThread.reset(); } }}
        onConfirm={() => { if (threadToDelete) deleteThread.mutate(threadToDelete.id); }}
        open={Boolean(threadToDelete)}
        pendingLabel="Deleting conversation…"
        subject={threadToDelete?.title}
        title="Delete conversation?"
      />
    </section>
  );
}

const visibilityLabels: Record<KnowledgeVisibility, string> = {
  restricted: "Restricted",
  admin: "Admins",
  analyst: "Analysts + Admins",
  viewer: "All roles",
};

function KnowledgeStatus({ document }: { document: KnowledgeDocument }) {
  return (
    <div className="text-right">
      <span className={cn(
        "inline-flex items-center gap-1.5 text-xs font-semibold capitalize",
        document.status === "ready" && "text-[#277056]",
        document.status === "failed" && "text-[#a54838]",
        ["queued", "processing"].includes(document.status) && "text-[#926918]",
      )}>
        {["queued", "processing"].includes(document.status) ? <LoaderCircle aria-hidden="true" className="animate-spin" size={12} /> : <span className="size-1.5 rounded-full bg-current" />}
        {document.status}
      </span>
      {document.status === "failed" && document.failure_reason ? <p className="mt-1 max-w-44 text-[10px] leading-4 text-[#9b5b50]">{document.failure_reason}</p> : null}
    </div>
  );
}

function KnowledgeView({ isAdmin }: { isAdmin: boolean }) {
  const queryClient = useQueryClient();
  const documents = useKnowledgeDocuments();
  const [showUpload, setShowUpload] = useState(false);
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File>();
  const [documentToDelete, setDocumentToDelete] = useState<KnowledgeDocument>();

  const upload = useMutation({
    mutationFn: ({ selectedFile, documentTitle }: { selectedFile: File; documentTitle: string }) =>
      uploadKnowledgeDocument(selectedFile, documentTitle),
    onSuccess(document) {
      queryClient.setQueryData<KnowledgeDocumentPage>(knowledgeKeys.documents, (current) => current
        ? { ...current, items: [document, ...current.items], total: current.total + 1 }
        : { items: [document], total: 1, limit: 50, offset: 0 });
      setFile(undefined);
      setTitle("");
      setShowUpload(false);
      void queryClient.invalidateQueries({ queryKey: knowledgeKeys.documents });
    },
  });

  const visibility = useMutation({
    mutationFn: ({ documentId, nextVisibility }: { documentId: string; nextVisibility: KnowledgeVisibility }) =>
      updateKnowledgeVisibility(documentId, nextVisibility),
    onSuccess(updated) {
      queryClient.setQueryData<KnowledgeDocumentPage>(knowledgeKeys.documents, (current) => current
        ? { ...current, items: current.items.map((item) => item.id === updated.id ? updated : item) }
        : current);
    },
  });

  const remove = useMutation({
    mutationFn: deleteKnowledgeDocument,
    onSuccess(_, documentId) {
      setDocumentToDelete(undefined);
      queryClient.setQueryData<KnowledgeDocumentPage>(knowledgeKeys.documents, (current) => current
        ? {
            ...current,
            items: current.items.filter((item) => item.id !== documentId),
            total: Math.max(0, current.total - 1),
          }
        : current);
    },
  });

  const ready = documents.data?.items.filter((document) => document.status === "ready").length ?? 0;
  const processing = documents.data?.items.filter((document) => ["queued", "processing"].includes(document.status)).length ?? 0;
  const lastReady = documents.data?.items
    .filter((document) => document.status === "ready")
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))[0];

  return (
    <div className="space-y-4">
      <section className="grid gap-px border border-[#d4d9d1] bg-[#d4d9d1] sm:grid-cols-3">
        <div className="bg-[#fbfcf8] p-5"><p className="text-xs text-[#75807b]">Visible sources</p><p className="mt-1 text-2xl font-semibold">{documents.data?.total ?? "—"}</p></div>
        <div className="bg-[#fbfcf8] p-5"><p className="text-xs text-[#75807b]">Ready</p><p className="mt-1 text-2xl font-semibold text-[#24684f]">{documents.data ? ready : "—"}</p><p className="mt-1 text-[11px] text-[#7d8883]">{processing > 0 ? `${processing} ingesting` : "No active ingestion"}</p></div>
        <div className="bg-[#fbfcf8] p-5"><p className="text-xs text-[#75807b]">Last indexed</p><p className="mt-1 text-lg font-semibold">{lastReady ? `${formatRecordDate(lastReady.updated_at)} UTC` : "No ready source"}</p></div>
      </section>

      {showUpload && isAdmin ? (
        <section className="border border-[#b9c9bf] bg-[#f8faf6] p-5">
          <div className="mb-4"><h2 className="font-semibold">Upload a private source</h2><p className="mt-1 text-xs text-[#74807a]">PDF or UTF-8 TXT, up to 10 MB. New sources remain restricted until you publish them.</p></div>
          <form className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)_auto] lg:items-end" onSubmit={(event) => { event.preventDefault(); if (file) upload.mutate({ selectedFile: file, documentTitle: title }); }}>
            <label className="grid gap-1.5 text-xs font-bold text-[#3f4a45]">Title <span className="font-normal text-[#89928e]">Optional</span><input className="h-10 border border-[#c9d1ca] bg-white px-3 text-sm font-normal outline-none focus:border-[#176b50]" maxLength={255} onChange={(event) => setTitle(event.target.value)} placeholder="Synthetic operations guide" value={title} /></label>
            <label className="grid gap-1.5 text-xs font-bold text-[#3f4a45]">File<input accept=".pdf,.txt,application/pdf,text/plain" className="h-10 border border-[#c9d1ca] bg-white px-2 py-2 text-xs font-normal file:mr-3 file:border-0 file:bg-[#e7eee9] file:px-2 file:py-1 file:text-xs file:font-bold file:text-[#245e4b]" onChange={(event) => setFile(event.target.files?.[0])} type="file" /></label>
            <div className="flex gap-2"><button className="h-10 bg-[#176b50] px-4 text-xs font-bold text-white disabled:opacity-60" disabled={!file || upload.isPending} type="submit">{upload.isPending ? "Uploading…" : "Upload source"}</button><button className="h-10 border border-[#ccd4cd] bg-white px-3 text-xs font-semibold" disabled={upload.isPending} onClick={() => { setShowUpload(false); setFile(undefined); setTitle(""); upload.reset(); }} type="button">Cancel</button></div>
          </form>
          {upload.isError ? <p className="mt-3 text-xs text-[#a33b32]" role="alert">{upload.error.message}</p> : null}
        </section>
      ) : null}

      <section className="border border-[#d4d9d1] bg-[#fbfcf8]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#e0e4dd] px-5 py-4"><div><h2 className="font-semibold">Workspace documents</h2><p className="mt-0.5 text-xs text-[#7b8581]">Only server-authorized sources are shown.</p></div>{isAdmin ? <button className="flex h-9 items-center gap-2 bg-[#176b50] px-3.5 text-xs font-bold text-white" onClick={() => { setShowUpload(true); upload.reset(); }} type="button"><FileText aria-hidden="true" size={15} />Upload source</button> : <span className="text-xs text-[#77827d]">Admin access is required to manage sources.</span>}</div>
        {documents.isPending ? <div className="space-y-3 p-5" role="status" aria-label="Loading knowledge documents">{Array.from({ length: 4 }).map((_, index) => <div key={index} className="h-16 animate-pulse bg-[#edf0eb]" />)}</div> : null}
        {documents.isError ? <div className="p-6 text-sm text-[#9b4336]" role="alert">Could not load knowledge documents. <button className="font-bold underline" onClick={() => void documents.refetch()} type="button">Retry</button></div> : null}
        {documents.data?.items.length === 0 ? <div className="grid min-h-56 place-items-center p-8 text-center"><div><BookOpenText aria-hidden="true" className="mx-auto text-[#71817a]" size={26} /><p className="mt-3 text-sm font-semibold">No visible knowledge sources</p><p className="mt-1 text-xs text-[#7b8681]">{isAdmin ? "Upload a PDF or TXT file to begin ingestion." : "An Admin must publish a source for your role."}</p></div></div> : null}
        <div className="divide-y divide-[#e4e7e1]">{documents.data?.items.map((document) => {
          const changingVisibility = visibility.isPending && visibility.variables?.documentId === document.id;
          const deleting = remove.isPending && remove.variables === document.id;
          const extension = document.original_filename.split(".").pop()?.toUpperCase() || "FILE";
          return <article key={document.id} className="grid gap-3 px-5 py-4 transition-colors hover:bg-[#f5f7f3] md:grid-cols-[40px_minmax(0,1fr)_190px_145px_auto] md:items-center"><div className="flex size-10 items-center justify-center border border-[#d4d9d1] bg-white text-[#507064]"><FileText aria-hidden="true" size={18} /></div><div className="min-w-0"><p className="truncate text-sm font-semibold text-[#303b36]">{document.title}</p><p className="mt-1 text-xs text-[#818b87]">{extension} · {formatFileSize(document.size_bytes)}{document.page_count ? ` · ${document.page_count} pages` : ""} · Updated {formatRecordDate(document.updated_at)} UTC</p></div><div>{isAdmin ? <label className="grid gap-1 text-[10px] font-bold uppercase tracking-[0.08em] text-[#7a8580]">Visibility<select aria-label={`Visibility for ${document.title}`} className="h-9 border border-[#ccd4cd] bg-white px-2 text-xs font-semibold normal-case tracking-normal outline-none disabled:opacity-60" disabled={changingVisibility || deleting} onChange={(event) => visibility.mutate({ documentId: document.id, nextVisibility: event.target.value as KnowledgeVisibility })} value={document.visibility}>{(Object.keys(visibilityLabels) as KnowledgeVisibility[]).map((value) => <option key={value} value={value}>{visibilityLabels[value]}</option>)}</select></label> : <p className="text-xs font-semibold text-[#65716c]">{visibilityLabels[document.visibility]}</p>}</div><KnowledgeStatus document={document} /><div className="flex justify-end">{isAdmin ? <button aria-label={`Delete ${document.title}`} className="flex size-9 items-center justify-center text-[#7d8883] hover:bg-[#faece9] hover:text-[#a33b32] disabled:opacity-50" disabled={deleting || changingVisibility} onClick={() => { remove.reset(); setDocumentToDelete(document); }} type="button">{deleting ? <LoaderCircle aria-hidden="true" className="animate-spin" size={16} /> : <Trash2 aria-hidden="true" size={16} />}</button> : null}</div></article>;
        })}</div>
        {visibility.isError ? <p className="border-t border-[#e0e4dd] px-5 py-3 text-xs text-[#a33b32]" role="alert">{visibility.error.message}</p> : null}
        {remove.isError && !documentToDelete ? <p className="border-t border-[#e0e4dd] px-5 py-3 text-xs text-[#a33b32]" role="alert">{remove.error.message}</p> : null}
      </section>
      <ConfirmationModal
        confirmLabel="Delete source"
        description="Delete this source file, every extracted chunk, and its indexed knowledge from the workspace."
        error={remove.isError ? remove.error.message : undefined}
        isPending={remove.isPending}
        onCancel={() => { if (!remove.isPending) { setDocumentToDelete(undefined); remove.reset(); } }}
        onConfirm={() => { if (documentToDelete) remove.mutate(documentToDelete.id); }}
        open={Boolean(documentToDelete)}
        pendingLabel="Deleting source…"
        subject={documentToDelete?.title}
        title="Delete knowledge source?"
      />
    </div>
  );
}

export function MockOpsPilotApp({ user, isLoggingOut, logoutError, onLogout }: MockOpsPilotAppProps) {
  const [view, setView] = useState<View>("overview");
  const [search, setSearch] = useState("");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const meta = viewTitles[view];
  const displayName = [user.first_name, user.last_name].filter(Boolean).join(" ") || user.email;
  const initials = `${user.first_name?.[0] ?? ""}${user.last_name?.[0] ?? ""}` || user.email[0]?.toUpperCase();
  const workspace = user.membership?.workspace.name ?? "No workspace";
  const firstName = user.first_name || "Operator";
  const openTicketCount = useTickets({ limit: 1, offset: 0, status: "open" });

  useEffect(() => {
    const focusSearch = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", focusSearch);
    return () => window.removeEventListener("keydown", focusSearch);
  }, []);

  const content = useMemo(() => {
    if (view === "overview") return <OverviewView setView={setView} />;
    if (view === "tickets") return <TicketsView search={search} />;
    if (view === "transactions") return <TransactionsView search={search} />;
    if (view === "conversations") return <ConversationsView />;
    return <KnowledgeView isAdmin={user.membership?.role === "admin"} />;
  }, [search, user.membership?.role, view]);

  const selectView = (nextView: View) => { setView(nextView); setSearch(""); setMobileNavOpen(false); };
  const updateSearch = (value: string) => {
    setSearch(value);
    const normalized = value.trim().toUpperCase();
    if (!normalized) return;
    if (normalized.startsWith("TXN")) {
      setView("transactions");
    } else if (view !== "tickets" && view !== "transactions") {
      setView("tickets");
    }
    setMobileNavOpen(false);
  };

  return (
    <div className="min-h-screen bg-[#eef0ea] text-[#17201d]">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[238px] flex-col border-r border-[#d3d8d1] bg-[#f8f9f5] lg:flex">
        <div className="flex h-[72px] items-center gap-3 border-b border-[#dfe3dc] px-5"><div className="flex size-9 items-center justify-center bg-[#184f3e] text-white"><Activity aria-hidden="true" size={19} /></div><div><p className="text-sm font-bold tracking-[-0.01em]">OpsPilot</p><p className="text-[10px] font-semibold uppercase tracking-[0.13em] text-[#73807a]">Control desk</p></div></div>
        <div className="px-4 py-5"><details className="group relative"><summary aria-label="Select workspace" className="flex w-full cursor-pointer list-none items-center gap-3 border border-[#d5dad3] bg-white px-3 py-2.5 text-left shadow-sm [&::-webkit-details-marker]:hidden"><span className="flex size-7 items-center justify-center bg-[#e0eee7] text-xs font-bold text-[#195b44]">{workspace.slice(0, 2).toUpperCase()}</span><span className="min-w-0 flex-1"><span className="block truncate text-xs font-bold">{workspace}</span><span className="mt-0.5 block text-[10px] text-[#7b8681]">Synthetic workspace</span></span><ChevronDown aria-hidden="true" size={14} className="text-[#78847e] transition-transform group-open:rotate-180" /></summary><div className="absolute inset-x-0 top-[calc(100%+6px)] z-40 border border-[#d5dad3] bg-white p-2 shadow-lg"><div className="flex items-center gap-2 bg-[#edf4ef] px-2.5 py-2 text-xs font-bold text-[#195b44]"><Check aria-hidden="true" size={14} /><span className="min-w-0 flex-1 truncate">{workspace}</span><span className="text-[9px] uppercase tracking-[0.08em]">Active</span></div><p className="px-2.5 pb-1 pt-2 text-[10px] leading-4 text-[#7b8681]">This account has one server-assigned workspace.</p></div></details></div>
        <nav aria-label="Main navigation" className="space-y-1 px-3">{navItems.map((item) => <button key={item.id} aria-current={view === item.id ? "page" : undefined} className={cn("group flex h-10 w-full items-center gap-3 px-3 text-sm font-semibold transition-colors", view === item.id ? "bg-[#e6efe9] text-[#14563f] shadow-[inset_2px_0_0_#176b50]" : "text-[#65716c] hover:bg-[#eef1ec] hover:text-[#26312c]")} onClick={() => selectView(item.id)} type="button"><item.icon aria-hidden="true" size={17} strokeWidth={1.8} />{item.label}{item.id === "tickets" && openTicketCount.data ? <span className="ml-auto flex min-w-5 items-center justify-center bg-[#f4e5e1] px-1.5 py-0.5 text-[10px] font-bold text-[#9b4336]">{openTicketCount.data.total}</span> : null}</button>)}</nav>
        <div className="mt-auto border-t border-[#dfe3dc] p-3"><div className="mb-2 flex items-center gap-3 px-2 py-2"><span className="flex size-8 shrink-0 items-center justify-center bg-[#dbe8e1] text-xs font-bold text-[#1c5a45]">{initials}</span><span className="min-w-0 flex-1"><span className="block truncate text-xs font-bold">{displayName}</span><span className="block truncate text-[10px] capitalize text-[#77827d]">{user.membership?.role ?? "No role"}</span></span></div>{logoutError ? <p className="mb-2 px-2 text-xs text-[#a33b32]" role="alert">{logoutError}</p> : null}<button className="flex h-9 w-full items-center gap-2 px-2 text-xs font-semibold text-[#6e7974] hover:bg-[#eef1ec] hover:text-[#9b4336] disabled:opacity-60" disabled={isLoggingOut} onClick={onLogout} type="button">{isLoggingOut ? <LoaderCircle aria-hidden="true" className="animate-spin" size={15} /> : <LogOut aria-hidden="true" size={15} />}{isLoggingOut ? "Signing out…" : "Sign out"}</button></div>
      </aside>

      <div className="lg:pl-[238px]">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-[#d4d9d1] bg-[#f8f9f5]/95 px-4 backdrop-blur sm:px-6 lg:h-[72px] lg:px-8">
          <button aria-expanded={mobileNavOpen} aria-label="Toggle navigation" className="flex size-9 items-center justify-center border border-[#d3d9d1] lg:hidden" onClick={() => setMobileNavOpen((open) => !open)} type="button">{mobileNavOpen ? <X aria-hidden="true" size={18} /> : <Menu aria-hidden="true" size={18} />}</button>
          <div className="flex items-center gap-2 lg:hidden"><span className="flex size-8 items-center justify-center bg-[#184f3e] text-white"><Activity aria-hidden="true" size={17} /></span><span className="text-sm font-bold">OpsPilot</span></div>
          <div className="ml-auto flex items-center gap-2 sm:gap-3"><label className="relative hidden md:block"><span className="sr-only">Search tickets or transactions</span><Search aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-[#7a8680]" size={15} /><input ref={searchInputRef} className="h-9 w-60 border border-[#cfd6ce] bg-white pl-9 pr-12 text-xs outline-none transition-colors placeholder:text-[#929b97] focus:border-[#176b50] xl:w-72" maxLength={view === "transactions" ? 32 : 100} onChange={(event) => updateSearch(event.target.value)} placeholder={view === "transactions" ? "Exact transaction reference…" : "Search tickets or TXN reference…"} type="search" value={search} /><span aria-hidden="true" className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-0.5 border border-[#d7dcd6] bg-[#f4f5f1] px-1.5 py-0.5 font-mono text-[9px] text-[#79847f]"><Command aria-hidden="true" size={9} />K</span></label><button className="hidden h-9 items-center gap-2 border border-[#d3d9d1] bg-white px-2.5 text-xs font-semibold sm:flex" type="button"><span className="flex size-5 items-center justify-center bg-[#dbe8e1] text-[9px] font-bold text-[#1c5a45]">{initials}</span>{firstName}<ChevronDown aria-hidden="true" size={13} /></button></div>
        </header>

        {mobileNavOpen ? <nav aria-label="Mobile navigation" className="fixed inset-x-0 top-16 z-30 border-b border-[#d4d9d1] bg-[#f8f9f5] p-3 shadow-lg lg:hidden">{navItems.map((item) => <button key={item.id} className={cn("flex h-11 w-full items-center gap-3 px-3 text-sm font-semibold", view === item.id ? "bg-[#e6efe9] text-[#14563f]" : "text-[#65716c]")} onClick={() => selectView(item.id)} type="button"><item.icon aria-hidden="true" size={17} />{item.label}</button>)}</nav> : null}

        <main className="mx-auto max-w-[1540px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#287059]">{meta.eyebrow}</p><h1 className="mt-1 text-2xl font-semibold tracking-[-0.035em] sm:text-[2rem]">{view === "overview" ? `${meta.title}, ${firstName}.` : meta.title}</h1><p className="mt-2 text-sm text-[#6e7974]">{meta.description}</p></div><div className="flex items-center gap-2"><span className="flex h-8 items-center gap-2 border border-[#d2d8d1] bg-[#f8f9f5] px-3 text-[11px] font-semibold text-[#65716c]"><Clock3 aria-hidden="true" size={13} />Updated just now</span><span className="hidden h-8 items-center gap-2 border border-[#b9d2c6] bg-[#e9f2ed] px-3 text-[11px] font-bold text-[#216047] sm:flex"><CircleDot aria-hidden="true" size={13} />Core workspace APIs live</span></div></div>
          {content}
        </main>
      </div>
    </div>
  );
}
