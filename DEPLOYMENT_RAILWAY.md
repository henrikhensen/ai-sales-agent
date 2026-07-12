# Deploying to Railway

A precise, minimal-click path to a public Railway deployment of this
project. Complements — does not replace — [`DEPLOYMENT.md`](./DEPLOYMENT.md)
(local/docker-compose runbook) and
[`docs/DEPLOYMENT_GUIDE.md`](./docs/DEPLOYMENT_GUIDE.md) (general
multi-provider orientation). Nothing in this file was actually run against a
real Railway account — creating the project, services, and domains below is
a deliberate action only you can take with your own Railway login.

**Safety carried over from every other phase, unchanged:** Mock/Safe Mode is
still the default for every provider. `EMAIL_INTEGRATION_PROVIDER=mock`,
`OUTREACH_DISPATCH_MODE=draft_only`, `OUTREACH_DISPATCH_ENABLE_REAL_SEND=false`
are the defaults below — this deployment adds **no** automatic sending, no
batch dispatch, and no send-capable endpoint. See
[`PROJECT_RULES.md`](./PROJECT_RULES.md).

## What you're creating

3 Railway services in one project:

| Service | Source | Purpose |
| --- | --- | --- |
| `backend` | this repo, root `Dockerfile` | FastAPI API |
| `frontend` | this repo, `frontend/Dockerfile` | Next.js UI |
| `Postgres` | Railway's managed Postgres plugin | the only stateful data store you must add |

Redis is **optional** — rate limiting already falls back to an in-memory
counter when Redis is unset or unreachable (fine for a single backend
instance, which is what a first deployment is). Add Railway's Redis plugin
only if you want `GET /ready` to report Redis as `up` or need shared
rate-limit counters across multiple backend instances later.

## 1. What to click in Railway

1. **New Project → Deploy from GitHub repo** → select this repository.
   Railway creates one service from the repo root; this becomes `backend`.
   - In that service's **Settings → Build**, confirm "Root Directory" is
     `/` (repo root). Rename the service to `backend`. The repo now ships
     a root [`railway.toml`](./railway.toml), which Railway auto-detects
     from that Root Directory and uses to pin the Dockerfile path, start
     command, and healthcheck path — no other Build/Deploy field needs
     manual entry.
2. **+ New → GitHub Repo** (same repo again) → this creates a second
   service; rename it `frontend`.
   - In `frontend`'s **Settings → Build**, set "Root Directory" to
     `frontend`. [`frontend/railway.toml`](./frontend/railway.toml) is
     then auto-detected the same way — again, no other Build/Deploy field
     needs manual entry.
   - **This Root Directory setting is the one manual step that decides
     whether you end up with one service or two.** If you skip creating
     the second service, or leave both services' Root Directory at `/`,
     Railway has no way to know a `frontend/` even exists — you'd get one
     (or two identical) backend deployments and no UI at all.
3. **+ New → Database → Add PostgreSQL.** Railway provisions it and exposes
   `${{Postgres.DATABASE_URL}}` for other services to reference.
4. *(Optional)* **+ New → Database → Add Redis** the same way, exposing
   `${{Redis.REDIS_URL}}`.
5. In `backend` → **Settings → Networking**, click **Generate Domain** to
   get a public `https://<backend>.up.railway.app` URL.
6. In `frontend` → **Settings → Networking**, click **Generate Domain** the
   same way for the public frontend URL.

That's the entire click path — everything else below is filling in
Variables tabs, which Railway treats as step 2 of the same flow.

## 2. Backend environment variables

`backend` service → **Variables** tab. Use
[`.env.production.example`](./.env.production.example) as the source list;
the ones you cannot skip:

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `DEBUG` | `false` |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (Railway variable reference — stays in sync automatically) |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` (only if you added the Redis plugin; otherwise leave unset) |
| `JWT_SECRET_KEY` | a real random secret — generate locally with `openssl rand -hex 32`, paste the *value* only, never commit it |
| `CORS_ALLOWED_ORIGINS` | the `frontend` service's public domain from step 1.6, e.g. `https://frontend-production-xxxx.up.railway.app` (exact origin, not `*`) |
| `FRONTEND_PUBLIC_URL` | same frontend domain (informational only) |
| `BACKEND_PUBLIC_URL` | `backend`'s own public domain from step 1.5 (informational only) |
| `LLM_PROVIDER` | `mock` (switch to `anthropic` + `ANTHROPIC_API_KEY` + `LLM_ENABLE_REAL_CALLS=true` only when you deliberately want billable real model calls) |
| `EMAIL_INTEGRATION_PROVIDER` | `mock` (stays disabled/safe by default) |
| `EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS` | `false` |
| `REPLY_TRACKING_PROVIDER` | `mock` |
| `REPLY_TRACKING_ENABLE_REAL_READS` | `false` |
| `OUTREACH_DISPATCH_MODE` | `draft_only` |
| `OUTREACH_DISPATCH_ENABLE_REAL_SEND` | `false` |
| `RATE_LIMIT_ENABLED` | `true` |
| `RATE_LIMIT_BACKEND` | `memory` (or `redis` if you added the Redis plugin) |

Do **not** set `PORT` yourself — Railway injects it automatically per
service, and both Dockerfiles already read `$PORT` at container start
(see the "Dockerfile changes" note below).

Every other variable in `.env.example` keeps its safe built-in default if
left unset (rate limits, quality scoring, data retention, etc.) — only
override one if you deliberately want different behavior.

## 3. Frontend environment variables

`frontend` service → **Variables** tab:

| Variable | Value |
| --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `backend`'s public domain from step 1.5, e.g. `https://backend-production-xxxx.up.railway.app` |

This is the one variable that matters for the frontend, and it must be
correct **before the first build** — Next.js inlines `NEXT_PUBLIC_*`
values into the browser bundle at build time, not at container start.
`frontend/Dockerfile` already declares `ARG NEXT_PUBLIC_API_BASE_URL`;
Railway automatically forwards a service Variable of the same name as a
build arg for Dockerfile-based services, so setting it in the Variables
tab is enough — no separate "build args" field to fill in. If you change
`NEXT_PUBLIC_API_BASE_URL` later, trigger a redeploy (a variable-only
change does not rebuild the image by itself).

## 4. Start commands

Both services already have a correct default `CMD` baked into their
Dockerfile — you do not need to set a custom Start Command in Railway's
service settings. For reference, this is what runs:

- **backend**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **frontend**: `node server.js` (the Next.js standalone server, which
  reads `$PORT`/`$HOSTNAME` itself)

**Dockerfile changes made for Railway**: both Dockerfiles previously
hardcoded port 8000/3000 in their `CMD`/`HEALTHCHECK` (exec-form `CMD`
arrays don't expand shell variables, so Railway's injected `$PORT` was
silently ignored before). `Dockerfile`'s `CMD` is now shell-form
(`uvicorn ... --port ${PORT:-8000}`) and its `HEALTHCHECK` reads `$PORT`
via Python; `frontend/Dockerfile`'s `HEALTHCHECK` reads `process.env.PORT`.
Local `docker compose` behavior is unchanged (`docker-compose.yml`
overrides the backend `command` explicitly; both still default to
8000/3000 when `PORT` is unset).

## 5. Migration command

`init_database()` still runs `CREATE TABLE IF NOT EXISTS` for every model
on **every** backend startup (unchanged, additive-only) — so a brand-new
Railway Postgres already has the full current schema after the backend's
first successful start. You do not have to run anything to get a working
schema. To keep Alembic (this project's path for real schema *changes*
going forward) in sync with that fact, run once, after the first
successful deploy:

```bash
# Install the CLI once (optional step; see section 6), then:
railway link                      # select this project when prompted
railway run --service backend -- python -m alembic stamp head
```

This records the current revision as already applied **without** running
any DDL (tables already exist via `init_database()`) — exactly the
"existing deployment" path in `DEPLOYMENT.md` section 5. From then on,
ship schema changes as a new Alembic revision and run
`railway run --service backend -- python -m alembic upgrade head` after
deploying it.

No CLI? Railway's dashboard does not expose an arbitrary one-off shell
today; use the CLI command above, or temporarily add a Railway **Deploy
Hook** / one-off **Job** running the same command if you prefer to stay
entirely in the browser.

## 6. Optional: Railway CLI

Not required — everything above works from the Railway dashboard alone.
The CLI is only more convenient for the migration command in section 5
and for tailing logs.

```bash
npm install -g @railway/cli   # or: brew install railway
railway login                 # opens a browser login — no secrets typed here
railway link                  # select this project + environment
railway status                # sanity-check you're linked to the right project
railway logs --service backend
```

Never run `railway variables set KEY=value` with a real secret value in a
shared terminal/log/CI output — set secrets through the dashboard's
Variables tab (masked) instead, or pipe them in without echoing:
`railway variables set JWT_SECRET_KEY="$(openssl rand -hex 32)"` (the
substitution happens locally in your shell and is never printed).

## 7. Health / login URLs to check after deploy

| URL | Expect |
| --- | --- |
| `https://<backend-domain>/health` | `{"status": "ok"}` |
| `https://<backend-domain>/ready` | `{"status": "ready", "database": "up", "redis": "up" or "down"}` — `redis: down` is fine if you skipped the Redis plugin |
| `https://<backend-domain>/docs` | Swagger UI loads |
| `https://<frontend-domain>/login` | Login page loads, and a login attempt reaches the backend (check the Network tab for a call to `<backend-domain>/api/v1/auth/login`, not `localhost`) |
| `https://<backend-domain>/api/v1/system/status` (admin, after logging in) | `production_warnings: []`, every `*_real_*_enabled` field `false`, every `*_provider` field `mock` |

If `/ready` never turns healthy: check `railway logs --service backend`
(or the dashboard's Deployments → Logs tab) — a missing/insecure
`JWT_SECRET_KEY`/`POSTGRES_PASSWORD`/`CORS_ALLOWED_ORIGINS` fails startup
loudly with a message naming exactly which variable is the problem, never
its value (see `backend/shared/production_checks.py`).

## 8. Domain / DNS (optional, beyond the free `*.up.railway.app` domains)

1. `frontend`/`backend` → **Settings → Networking → Custom Domain** → enter
   your domain (e.g. `app.yourdomain.com` / `api.yourdomain.com`).
2. Add the CNAME record Railway shows you at your DNS provider.
3. Once DNS resolves, update `CORS_ALLOWED_ORIGINS` (backend) and
   `NEXT_PUBLIC_API_BASE_URL` (frontend, requires a redeploy since it's
   build-time) to the new domains, replacing the `*.up.railway.app` ones.
4. Railway issues a TLS certificate for the custom domain automatically —
   no separate Caddy/nginx step needed (unlike the self-managed VPS option
   in `docs/DEPLOYMENT_GUIDE.md`).

## 9. Acceptance test (do this once, end to end)

1. Open `https://<frontend-domain>/login`, log in with a seeded/admin
   account (see `scripts/seed_demo_data.py` if you need one).
2. Confirm the home page's Safety Strip shows Safe/Mock Mode, "kein
   automatischer Versand", Human Review required, Do-not-contact active.
3. Run the Lead Finder once end to end (mock mode) and confirm a run
   completes and shows candidates — proves frontend → backend → Postgres
   all actually connected across their separate Railway services, not just
   that each health check passed individually.
4. Check `GET /api/v1/system/status` (section 7) one more time after that
   run to confirm no provider silently switched to real/enabled.

## 10. Troubleshooting: crash loop right after deploy

**Real incident, root cause confirmed by code inspection
(`backend/shared/config.py:database_url`, `backend/infrastructure/
database/session.py:init_database`,
`backend/shared/production_checks.py:validate_production_config`):**
pasting the local `.env` file's contents directly into the `backend`
service's Railway Variables tab. Two of those local-only values break a
Railway deploy:

- **`POSTGRES_HOST=postgres`** (and `REDIS_HOST=redis`) are the
  `docker-compose.yml` *service names* — they only resolve inside that
  compose network. On Railway there is no host literally named
  `postgres`. Without `DATABASE_URL` set, `Settings.database_url` builds
  a connection string from `POSTGRES_HOST` and asyncpg fails DNS
  resolution. `backend/main.py`'s `lifespan` awaits `init_database()`
  before the app can serve a single request, so this failure happens
  during startup, not on some later request — the container exits
  non-zero immediately and Railway shows a crash loop.
- **If `APP_ENV=production` was also set** while `POSTGRES_PASSWORD` was
  still left at its local example value (`sales_agent_password`) and no
  `DATABASE_URL` was set, `validate_production_config` raises
  `ProductionConfigError` even earlier (at module import, before
  `lifespan` even runs) with the exact message *"POSTGRES_PASSWORD is
  missing or still the example default."* — check the deploy logs for
  this line specifically; it is the fastest, clearest signal if present.

**Fix:** on the `backend` service's Variables tab, delete
`POSTGRES_HOST`/`POSTGRES_PORT`/`POSTGRES_USER`/`POSTGRES_PASSWORD`/
`POSTGRES_DB`/`REDIS_HOST`/`REDIS_PORT`/`REDIS_DB` entirely if present,
and set only `DATABASE_URL=${{Postgres.DATABASE_URL}}` (and, only if you
added the Redis plugin, `REDIS_URL=${{Redis.REDIS_URL}}`) — see section 2.
`DATABASE_URL`/`REDIS_URL` always take precedence over the discrete
`POSTGRES_*`/`REDIS_*` vars when set, so there's no need to unset the
latter for correctness, but removing them avoids exactly this kind of
confusion later.

**A single service where you expected two, or an unexpected/odd port
shown under Networking:** almost always means the `frontend` service was
never created as its own service with Root Directory `frontend` — Railway
was left building only the repo-root Dockerfile (backend) for whatever
service exists, sometimes with a build-tool auto-detection guess replacing
the intended Dockerfile build. Fix: follow section 1 exactly — two
separate Railway services, each with its own Root Directory, each now
carrying its own `railway.toml` (added in this fix) that pins the
Dockerfile path/start command/healthcheck explicitly, removing any
auto-detection guesswork. Also check the `PORT` variable on both
services' Variables tabs — if either has a manually-set `PORT` value,
delete it; Railway assigns and injects `PORT` itself, and both
Dockerfiles already read it (`$PORT`, defaulting to 8000/3000 only when
unset, e.g. locally).
