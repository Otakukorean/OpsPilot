# OpsPilot implementation decisions

## Roadmap authority

`MILESTONES.md` is the authoritative implementation sequence. The SRS and TDD
define product and architecture requirements, but their older roadmap labels do
not override the milestone order.

## P1 conversation boundary

The initial conversation slice persists owned threads and user-authored messages.
Posting a message returns the stored user message only. Assistant generation,
streaming, citations, RAG, LangGraph, and external model calls remain deferred to
their later authoritative milestones.

Conversation authorization is owner-only within the active workspace resolved
from the authenticated session. Workspace administrators do not implicitly bypass
thread ownership; an explicit, separately tested admin authorization policy would
be required before that behavior is introduced.

## P1 audit boundary

Permission decisions for operations and conversations are persisted as structured,
metadata-only `AuditEvent` rows in addition to JSON operational logs. Audit events
deliberately have no generic metadata or payload JSON field, preventing callers
from accidentally storing search text, message bodies, document text, or resource
contents. Workspace Admins may read only the audit events belonging to their
server-resolved active workspace.

## P2 knowledge and RAG boundary

`MILESTONES.md` remains authoritative: document ingestion and retrieval are P2,
while LangGraph, LLM-generated answers, chat streaming, and the frontend remain
P3. P2 returns citation-ready evidence and an explicit `insufficient_evidence`
result; it does not generate an assistant answer.

Uploads accept text-based PDF and UTF-8 TXT only, are limited to 10 MiB and 100
PDF pages by default, and are stored in a private Docker volume rather than a
public media route. Documents start `restricted`. Publishing uses a role floor:
`admin` is visible to Admins, `analyst` to Admins and Analysts, and `viewer` to all
three workspace roles. Restricted documents are excluded from retrieval for every
role until published.

The initial swappable embedding adapter is `local_hashing_v1`, a deterministic
384-dimensional offline lexical embedder. It makes local development, pgvector
integration, isolation tests, and evidence thresholds reproducible without adding
a live provider or secret. It is not production-quality semantic retrieval. A
hosted embedding adapter and model/version migration require an explicit provider
decision; vectors from different models must not share a retrieval partition.

Exact filtered pgvector search is used for the synthetic MVP. SQL filters enforce
the authenticated workspace, ready ingestion state, embedding model, and published
role visibility before any chunk becomes API evidence. No approximate vector index
is added until profiling demonstrates a need and filtered recall is tested.

## P3 constrained agent boundary (first slice)

The first P3 increment is a synchronous backend vertical slice. It uses a bounded
LangGraph state graph and the OpenAI Responses API with `gpt-6-luna` as the
environment-configurable default. Streaming and the React/TanStack connection were
intentionally sequenced after the secure agent contract; the synchronous UI
connection is documented below, while streaming remains deferred.

The model can request exactly `search_knowledge`, `get_transaction`, and
`search_tickets`. Their strict schemas reject extra fields, including attempted
workspace injection. Every invocation freshly resolves the actor's active
membership; workspace and role never come from prompt or tool arguments. There is
no generic HTTP, SQL, shell, write, payment, email, or arbitrary-code tool.

Call-count, output-token, timeout, and result limits are enforced in code rather
than only in the system prompt. Unsupported answers are replaced with a fixed
abstention. Knowledge citations are persisted only after a second server-side
workspace/status/visibility validation. Run and tool audit models deliberately
exclude prompts, message bodies, tool inputs, and tool outputs.

The P1 message-storage endpoint remains unchanged for backward compatibility.
P3 generation is exposed separately at
`POST /chat/threads/{thread_id}/agent-runs`, making the cost-bearing operation
explicit and allowing streaming to be introduced later without changing P1.

## P3 synchronous agent UI connection

The conversation composer now invokes the protected agent-run endpoint directly
instead of first calling the P1 message-storage endpoint. The agent endpoint owns
creation of both the user turn and assistant response, which prevents duplicate
user messages. The UI shows an optimistic question and bounded pending state,
then reloads persisted history and server-validated citations. Provider failures
remain sanitized and the stored question stays visible in history. Streaming is
still deferred; this slice uses the existing synchronous endpoint.

The agent and knowledge modules previously exposed two different OpenAPI schemas
with the same `CitationOut` component name. The agent schema is now named
`AgentCitationOut`, and message-history responses include those persisted citation
fields so Swagger and the generated TypeScript client match runtime behavior.

## P3 knowledge management UI connection

The frontend Knowledge view now lists the documents authorized by the backend and
polls only while an ingestion job is queued or processing. Admins can upload bounded
PDF or TXT files, change document visibility, and delete sources. Analyst and Viewer
clients do not render management controls and receive only documents published for
their role. All requests use the authenticated session and CSRF protection without
accepting a workspace identifier from the browser; Django remains authoritative for
workspace membership and object-level access.

## P3 agent security and evaluation gate

Agent security controls remain outside model instructions. Before a run is reserved,
the backend locks the authenticated user row and atomically enforces a per-user request
rate, recent concurrent-run ceiling, and rolling token budget. Rejected requests create
metadata-only audit events, return a generic `429`, do not call the provider, and do not
store the rejected question. Per-run LLM-call, tool-call, output-token, cumulative-token,
and provider-timeout limits remain separately enforced.

The deterministic security suite uses only fictional fixtures and fake model responses.
It covers indirect prompt injection requesting URL exfiltration, non-allowlisted tools,
foreign transaction IDs, role downgrades, membership changes, restricted/foreign citation
revalidation, usage limits, timeout sanitization, and escaped frontend rendering. It never
uses the live OpenAI API. Tool and run audit records continue to exclude prompts, tool
arguments, tool results, and document contents.

## P3 frontend foundation

The frontend is a separate `frontend/` Next.js App Router application using
TypeScript. TanStack Query owns server-state caching and TanStack Table will power
data grids. Next.js remains the sole router; TanStack Router is intentionally not
installed. React Hook Form and Zod provide bounded form validation, while
`openapi-typescript` and `openapi-fetch` provide a generated API contract.

Development uses the same public-origin shape intended for deployment: the browser
calls `/api` on Next.js, and Next.js proxies that path to Django. This lets Django
session and CSRF cookies remain first-party. Compose allowlists only its internal
`backend` hostname and the two local frontend development origins.

No component system or product UI is selected in this setup slice. That decision
is deferred until the login and application-shell design direction is implemented,
avoiding a broad UI dependency before the interaction and accessibility needs are
known.
