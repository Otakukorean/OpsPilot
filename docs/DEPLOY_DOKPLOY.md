# Deploy OpsPilot to a VPS with Dokploy

OpsPilot ships a separate `compose.prod.yaml` for production. The existing
`compose.yaml` remains the local development stack.

## 1. Prepare the domain and repository

1. Push the repository to GitHub.
2. Create an `A` record for the application domain pointing to the VPS.
3. In Dokploy, create a **Docker Compose** service from the repository and select
   `./compose.prod.yaml` as the Compose path.
4. Enable Dokploy's isolated deployment option when available.

For a manual VPS deployment using Dokploy's existing Traefik instance, install
`infra/traefik/opspilot.yml` into `/etc/dokploy/traefik/dynamic/`. The file routes
`opspilot.ahmed-alsaleem.site` to the Nginx gateway on `dokploy-network`.

The production stack publishes no host ports. PostgreSQL, Redis, Django, the
frontend, and the Celery worker stay on private Docker networks. Nginx is the
only application gateway attached to Dokploy's external network.

## 2. Configure production environment variables

Add these values in the Dokploy Compose service's **Environment** editor. Dokploy
writes them to the `.env` file loaded by the backend and worker containers.

```dotenv
DJANGO_SECRET_KEY=generate-a-long-random-value-of-at-least-50-characters
DJANGO_ALLOWED_HOSTS=opspilot.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://opspilot.example.com
DJANGO_LOG_LEVEL=INFO
DJANGO_HSTS_SECONDS=3600

POSTGRES_DB=opspilot
POSTGRES_USER=opspilot
POSTGRES_PASSWORD=generate-a-separate-strong-random-password
POSTGRES_CONN_MAX_AGE=60

OPSPILOT_DEMO_PASSWORD=use-a-strong-demo-only-password
# Intentionally public on the login page. Never reuse a private password.
OPSPILOT_TESTER_EMAIL=tester@atlaspay.example
OPSPILOT_TESTER_PASSWORD=choose-a-public-demo-only-password
OPENAI_API_KEY=your-openai-api-key
OPENAI_CHAT_MODEL=gpt-6-luna

OPSPILOT_PRIVATE_MEDIA_ROOT=/app/private_media
KNOWLEDGE_MAX_UPLOAD_BYTES=10485760
KNOWLEDGE_MAX_PDF_PAGES=100
KNOWLEDGE_EMBEDDING_PROVIDER=local_hashing_v1
KNOWLEDGE_MIN_SIMILARITY=0.15

AGENT_MAX_LLM_CALLS=4
AGENT_MAX_TOOL_CALLS=3
AGENT_REQUEST_TIMEOUT_SECONDS=30
AGENT_MAX_TOTAL_TOKENS=12000
AGENT_MAX_CONCURRENT_RUNS=2
AGENT_RATE_LIMIT_REQUESTS=20
AGENT_RATE_LIMIT_WINDOW_SECONDS=3600
AGENT_USER_TOKEN_BUDGET=100000
AGENT_TOKEN_BUDGET_WINDOW_SECONDS=86400

GUNICORN_WORKERS=2
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=120
```

Generate secrets locally without storing them in shell history or the repository:

```bash
openssl rand -base64 48
```

Do not copy development values from the local `.env`. The production Compose
file forces debug mode off, HTTPS redirects on, and secure cookies on.

## 3. Add the Dokploy domain

In the Compose service's **Domains** tab, add the public domain with:

- Service: `proxy`
- Container port: `8080`
- Path: `/`
- HTTPS: enabled
- Certificate: Let's Encrypt

Redeploy after adding or changing the domain. Nginx sends `/api`, `/admin`,
`/static`, and `/health` to private Django and all other requests to private
Next.js. The backend and frontend must not receive separate public domains.

## 4. Deploy and seed the fictional demo

Deploy the Compose service. The backend startup command automatically runs
database migrations and collects admin static files before starting Gunicorn.
The pgvector extension is created by the Django knowledge migration.

After the first healthy deployment, open the Dokploy terminal for the `backend`
service and run:

```bash
python manage.py seed_synthetic_data
```

The command is idempotent and requires `OPSPILOT_DEMO_PASSWORD`. It also creates
the public tester as a non-staff Analyst in AtlasPay Demo using
`OPSPILOT_TESTER_EMAIL` and `OPSPILOT_TESTER_PASSWORD`. Those tester credentials
are intentionally embedded into the public frontend image, so never reuse a
private password or promote the tester to Admin.

## 5. Verify the deployment

Check the following from a private browser window:

1. `https://opspilot.example.com/` loads the login screen.
2. Login succeeds with one seeded demo account.
3. Tickets and transactions load and remain workspace-scoped.
4. A PDF/TXT upload reaches `ready` status through the Celery worker.
5. One grounded assistant request completes without exposing unrestricted data.
6. `https://opspilot.example.com/admin/` loads its static assets.
7. HTTP redirects to HTTPS and session cookies are marked `Secure` and
   `HttpOnly` (the CSRF cookie intentionally remains readable by the frontend).

The backend and frontend containers include health checks. Dokploy should show
the database, Redis, backend, worker, and frontend services running; database and
Redis also report explicit health status.

## 6. Backups and maintenance

Configure Dokploy backups for at least these named volumes:

- `postgres_data` — application records, accounts, audit metadata, and vectors.
- `private_uploads` — private synthetic PDF/TXT source files.

The Redis volume is useful for queue durability but is not the system of record.
Before upgrading, back up PostgreSQL and private uploads. After the domain has
served HTTPS reliably, `DJANGO_HSTS_SECONDS` can be increased gradually. Do not
enable HSTS subdomains or preload unless every subdomain is permanently HTTPS.
