# OpsPilot

## Production deployment

The production stack for a VPS running Dokploy is defined in
`compose.prod.yaml`. It uses production Next.js, Gunicorn, WhiteNoise, private
service networking, persistent data volumes, automatic migrations/static
collection, secure proxy settings, and container health checks. Follow
[`docs/DEPLOY_DOKPLOY.md`](docs/DEPLOY_DOKPLOY.md) for the required Dokploy
environment and domain configuration.

## Local infrastructure

Create a local environment file before starting the services:

```bash
cp .env.example .env
```

Replace the placeholder secret and password values in `.env`, then start PostgreSQL with pgvector, Redis, Django, and Celery:

```bash
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_synthetic_data
```

The Next.js frontend is available at <http://127.0.0.1:3000/>. Django remains
available directly at <http://127.0.0.1:8000/> for backend development. Browser
requests should normally use the frontend origin, which proxies `/api` to Django.

## Frontend development

The P3 frontend foundation lives in `frontend/` and uses Next.js App Router,
TypeScript, Tailwind CSS, TanStack Query, TanStack Table, React Hook Form, Zod,
and an OpenAPI-generated typed client. Next.js owns routing, so TanStack Router is
intentionally not installed.

Docker Compose starts the frontend automatically. To run it directly instead:

```bash
cd frontend
npm ci
npm run dev
```

When the Django schema changes and the backend is running, refresh the generated
API types with:

```bash
npm run api:generate
```

Frontend quality commands are:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

The current frontend integrates session authentication, tickets, transactions,
owner-scoped conversations, synchronous agent generation, and knowledge management.
Unsafe writes establish a CSRF cookie before calling Django, and the browser never
supplies workspace or owner identifiers. Knowledge uploads accept PDF and TXT files
up to 10 MB; Admins can change visibility or delete sources, while other roles only
receive sources published for them. Response streaming remains deferred.

## Accounts API

Interactive Swagger documentation is available at
<http://127.0.0.1:8000/api/v1/docs>. The raw OpenAPI schema is available at
<http://127.0.0.1:8000/api/v1/openapi.json>.

The initial account endpoints are:

- `GET /api/v1/auth/csrf` — set the CSRF cookie before an unsafe request.
- `POST /api/v1/auth/login` — create a database-backed session using email and password.
- `POST /api/v1/auth/logout` — end the authenticated session.
- `GET /api/v1/me` — return the authenticated user and server-resolved active workspace membership.

## Synthetic operations API

The operations API exposes read-only detail and scoped query endpoints:

- `GET /api/v1/transactions` — filter by exact `code` and/or `status`.
- `GET /api/v1/transactions/{transaction_id}`
- `GET /api/v1/tickets` — search by `query` and/or filter by `status`.
- `GET /api/v1/tickets/{ticket_id}`

Both endpoints require an authenticated Admin or Analyst. The backend resolves the
workspace from the user's active membership; it never accepts a workspace ID from
the client. A record from another workspace returns the same generic `404` as an
unknown ID, and Viewers receive `403`.

Query endpoints return `items`, `total`, `limit`, and `offset`. Pagination is
bounded to 1–50 records per request. Ticket search uses only fixed ORM filters;
there is no arbitrary SQL or client-controlled field selection.

## Conversations API

The P1 conversation API persists threads and user-authored messages:

- `POST /api/v1/chat/threads`
- `GET /api/v1/chat/threads`
- `GET /api/v1/chat/threads/{thread_id}`
- `DELETE /api/v1/chat/threads/{thread_id}`
- `GET /api/v1/chat/threads/{thread_id}/messages`
- `POST /api/v1/chat/threads/{thread_id}/messages`

Threads are visible only to their owner in the workspace resolved from the active
session membership. Guessed IDs belonging to another user or workspace return a
generic `404`. Writes require Django's CSRF token. List endpoints use bounded
`limit` and `offset` pagination with a maximum page size of 50.

Posting to the P1 `/messages` endpoint still only stores a user message. P3 agent
generation uses the separate endpoint documented below.

Deleting a thread is CSRF-protected, owner-only, and also deletes its messages.
Denied deletion attempts return the same generic `404` used for unknown IDs.

## Audit API

Allowed and denied operations and conversation policy decisions are stored as
immutable, metadata-only audit events. Workspace Admins can query their active
workspace's events at:

- `GET /api/v1/admin/audit`

Filters include exact `action`, `outcome`, and `resource_type`, with bounded
`limit` and `offset` pagination. Analysts and Viewers receive `403`, and the
workspace is always derived from the authenticated membership. Audit rows contain
internal identity, action, outcome, safe reason code, request ID, duration, and
timestamp. They never contain search text, titles, messages, request bodies,
credentials, or ticket/transaction contents.

## Knowledge and RAG API (P2)

P2 adds private, workspace-scoped document ingestion and citation-ready retrieval:

- `POST /api/v1/documents` — Admin-only multipart PDF/TXT upload (`file`, optional `title`).
- `GET /api/v1/documents` — list visible metadata; Admins also see restricted uploads.
- `GET /api/v1/documents/{document_id}` — read permitted metadata; no storage URL is exposed.
- `PATCH /api/v1/documents/{document_id}/visibility` — Admin-only publish/restrict operation.
- `DELETE /api/v1/documents/{document_id}` — delete the source, chunks, and embeddings.
- `GET /api/v1/knowledge/search?query=...&limit=5` — return authorized evidence with title, page when available, bounded excerpt, and similarity score.

Uploads are restricted by default and processed by Celery through
`queued -> processing -> ready` or `failed`. PDF/TXT signature, MIME type, size,
encoding, encryption, and PDF page-count checks happen before private storage.
Text extraction, overlapping chunking, embedding, and atomic vector replacement
happen in the worker. OCR is intentionally not included.

Publishing is hierarchical within the authenticated workspace: `admin` is visible
to Admins, `analyst` to Admins and Analysts, and `viewer` to all roles. Restricted,
queued, failed, foreign-workspace, and role-forbidden chunks cannot enter search
results. Unknown and guessed foreign document IDs return the same generic `404`.

The development embedder is the deterministic, offline `local_hashing_v1` adapter.
It verifies the complete pgvector pipeline without a third-party provider or API
key. It is suitable for the fictional demo and automated isolation tests, not a
claim of production semantic quality.

## Constrained agent API (P3, first slice)

The first P3 slice adds a synchronous, grounded assistant endpoint:

- `POST /api/v1/chat/threads/{thread_id}/agent-runs` with `{"text": "..."}`

The endpoint is session-authenticated, CSRF-protected, and owner-only. It runs a
bounded LangGraph loop through the OpenAI Responses API and can invoke exactly
three read-only tools: authorized knowledge search, one transaction lookup, and
ticket search. Workspace identity is never accepted from the client or model.
Membership and role are re-resolved before every tool invocation. Admins and
Analysts may use operations tools; all active roles may search knowledge subject
to document visibility.

Set these values in `.env` before making an agent request:

```dotenv
OPENAI_API_KEY=your-key
OPENAI_CHAT_MODEL=gpt-6-luna
OPENAI_MAX_OUTPUT_TOKENS=800
AGENT_MAX_LLM_CALLS=4
AGENT_MAX_TOOL_CALLS=3
AGENT_REQUEST_TIMEOUT_SECONDS=30
AGENT_MAX_TOTAL_TOKENS=12000
AGENT_MAX_CONCURRENT_RUNS=2
AGENT_RATE_LIMIT_REQUESTS=20
AGENT_RATE_LIMIT_WINDOW_SECONDS=3600
AGENT_USER_TOKEN_BUDGET=100000
AGENT_TOKEN_BUDGET_WINDOW_SECONDS=86400
```

The answer is persisted as an assistant message. Knowledge citations are rebuilt
from authorized database rows after generation; model-authored identifiers cannot
create citations. If no authorized evidence was obtained, the server replaces the
answer with a fixed abstention. Agent-run and tool-invocation records contain only
model/call/token/timing/outcome metadata—not prompts, tool arguments, results,
document text, or secrets.

Per-user agent reservations are serialized in PostgreSQL and checked against the
configured request, concurrency, and rolling token limits before a question is stored
or a provider call is made. Limit rejections return `429` with a generic message and
record only a safe audit reason. Run the deterministic adversarial gate with:

```bash
docker compose exec backend python manage.py test apps.agents.tests
```

The suite uses fake model responses and synthetic prompt-injection fixtures; it never
consumes OpenAI credits or attempts an outbound exfiltration request.

Automated tests use fake model responses and never consume OpenAI credits. The
React/TanStack conversation composer calls this endpoint directly, shows a bounded
pending/error state, and refreshes persisted messages and server-validated
citations after completion. Streaming transport remains a later P3 slice.

The private source volume is named `opspilot_private_uploads`. Configuration is in
`.env.example`; defaults are 10 MiB, 100 PDF pages, five retrieval results, and a
minimum similarity of `0.15`.

After changing `api/requirements.txt`, regenerate and review
`api/requirements.lock`; Docker installs the fully resolved lockfile.

Set `OPSPILOT_DEMO_PASSWORD`, `OPSPILOT_TESTER_EMAIL`, and
`OPSPILOT_TESTER_PASSWORD` in `.env`, then run the idempotent seed command:

```bash
docker compose exec backend python manage.py seed_synthetic_data
```

It creates two entirely fictional workspaces, three role-based users per workspace,
one additional public non-staff Analyst tester in AtlasPay Demo, synthetic
transactions, and synthetic tickets. The workspaces
intentionally contain overlapping display codes to demonstrate that access is
scoped by workspace.

Browser clients must include credentials so the session and CSRF cookies are sent.
For login, logout, and future unsafe requests, copy the `csrftoken` cookie value to
the `X-CSRFToken` request header. Swagger handles this header automatically after
the CSRF endpoint has been called.

## Logging

Django, account audit events, and Celery write structured JSON logs to stdout.
Request logs contain a generated request ID, method, path, status, duration, and
the authenticated internal user ID when available. Authentication logs contain
outcomes and internal IDs, but never request bodies, passwords, cookies, CSRF
tokens, session IDs, or failed-login email addresses.

Set `DJANGO_LOG_LEVEL` to `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.
The default is `INFO`. Follow the local logs with:

```bash
docker compose logs --follow backend worker
```

Check service status and logs:

```bash
docker compose ps
docker compose logs backend worker
```

Stop the services without deleting database or Redis data:

```bash
docker compose down
```

To also delete the local Docker data volumes, run `docker compose down --volumes`.
