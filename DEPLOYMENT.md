# Deployment Runbook

Step-by-step operational instructions for running this project locally, in
a production-shaped local build, and via `docker-compose.prod.yml`. For a
comparison of actual cloud hosting targets (Render, Railway, Fly.io, a VPS,
AWS), see [`docs/DEPLOYMENT_GUIDE.md`](./docs/DEPLOYMENT_GUIDE.md). For the
checklist of things to decide/change before real traffic, see
[`docs/PRODUCTION_CHECKLIST.md`](./docs/PRODUCTION_CHECKLIST.md).

Contains no real credentials, no cloud-specific configuration, and creates
no cloud resources. Real deployment credentials (a managed Postgres URL,
API keys, a domain) always come from your own hosting target's secret
store — never from this repository.

## 1. Local development

```powershell
# First time: copy the example env file
Copy-Item .env.example .env

# Build and start backend + frontend + Postgres + Redis
powershell -File scripts\docker-up.ps1
# — or directly —
docker compose up --build -d
```

- Backend: http://localhost:8000 (Swagger at `/docs`)
- Frontend: http://localhost:3000
- `docker-compose.yml` bind-mounts `backend/` and `tests/` and runs
  `uvicorn --reload`, so backend code edits apply without a rebuild.
- Mock LLM, mock Email Draft Integration, and mock Reply Tracking are all
  on by default — nothing here costs money or touches a real external
  account until you deliberately change `.env`.

Stop the stack: `docker compose down` (data survives — see volumes below).

## 2. Test a production build locally

Before ever touching `docker-compose.prod.yml`, confirm both images build
cleanly:

```powershell
# Backend tests (no Docker needed)
python -m pytest -q

# Frontend type-check + production build (no Docker needed)
cd frontend
npm run typecheck
npm run build
cd ..

# Full production-shaped image build (same Dockerfiles docker-compose.prod.yml uses)
docker compose build
```

## 3. `docker-compose.prod.yml`

Structural hardening only — not a deployable cloud configuration. Compared
to `docker-compose.yml`: no bind-mounted source (runs the built image
as-is), no `--reload`, Postgres/Redis ports are not published to the host,
`restart: always` instead of `unless-stopped`, and the backend/frontend
containers wait for each other's Docker healthcheck (`condition:
service_healthy`) before starting.

```bash
# Create a real .env first (never commit it) — see section 4.
docker compose -f docker-compose.prod.yml --env-file .env up --build -d
```

Validate the compose file itself at any time (no containers started):

```bash
docker compose -f docker-compose.prod.yml config --quiet
```

Put a reverse proxy (Caddy, nginx) in front for TLS termination — this
compose file does not terminate TLS itself.

## 4. Environment variables

See `.env.example` for the full, documented list with safe local defaults.
The ones that matter most when moving toward production:

| Variable | Local default | Production guidance |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` — enables the startup warnings below |
| `DEBUG` | `true` | `false` |
| `JWT_SECRET_KEY` | insecure placeholder | a real random secret (e.g. `openssl rand -hex 32`) |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | exact production frontend origin(s), never `*` |
| `POSTGRES_PASSWORD` | example password | a real, unique password |
| `DATABASE_URL` | unset (built from `POSTGRES_*`) | set this instead if your host injects one connection string |
| `REDIS_URL` | unset (built from `REDIS_*`) | same, for a managed Redis |
| `FRONTEND_PUBLIC_URL` / `BACKEND_PUBLIC_URL` | localhost | your real domains (informational; shown in system status) |
| `LLM_PROVIDER` / `LLM_ENABLE_REAL_CALLS` | `mock` / `false` | change only when deliberately paying for real model calls |
| `EMAIL_INTEGRATION_PROVIDER` / `EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS` | `mock` / `false` | change only when deliberately connecting Gmail/Outlook |
| `REPLY_TRACKING_PROVIDER` / `REPLY_TRACKING_ENABLE_REAL_READS` | `mock` / `false` | change only when deliberately reading a real mailbox |
| `ENABLE_METRICS` / `ENABLE_BACKUPS` | `false` / `false` | turn on once you're actually watching them |

At `APP_ENV=production` startup, the backend logs a warning (never a
crash) for each unsafe setting still in place — see
`backend/shared/production_checks.py`. The same list is available live,
without reading logs, at `GET /api/v1/system/status` (`production_warnings`,
admin-only).

## 5. Database & Redis volumes

- `postgres_data` and `redis_data` are named Docker volumes — data survives
  `docker compose down` and container rebuilds. Only `docker compose down
  -v` (or manually removing the volume) deletes them.
- No migration framework (Alembic) yet — `init_database()` runs `CREATE
  TABLE IF NOT EXISTS` for every model on startup. Adding a new table is
  automatic on the next restart; changing an existing column requires a
  manual `ALTER TABLE` (see `docs/PRODUCTION_CHECKLIST.md`).
- For real production use, move to a managed Postgres/Redis instance
  instead of these containers (see `docs/DEPLOYMENT_GUIDE.md`) — the
  `DATABASE_URL`/`REDIS_URL` overrides in section 4 exist for exactly this.

## 6. Health & readiness checks

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Unprefixed liveness alias — always 200 if the process is up |
| `GET /ready` | Unprefixed readiness — 503 if Postgres or Redis is unreachable |
| `GET /api/v1/health` | Liveness + component status (JSON body, always 200) |
| `GET /api/v1/ready` | Same readiness check, under the versioned API prefix |
| `GET /api/v1/system/status` | Admin-only: app/provider/safe-mode snapshot |

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
curl -s http://localhost:8000/api/v1/ready
```

Point uptime monitoring (UptimeRobot, Better Uptime, your host's built-in
health check) at `/health` for liveness and `/ready` for whether it should
receive traffic.

## 7. Logs

Structured stdout logging (`backend/shared/logging.py`) — captured
automatically by `docker compose logs` or any hosting provider's log
viewer. Per-request access lines (`backend.requests` logger) include a
request id, method, path, status, duration, and a best-effort user id
decoded from the JWT — never the token, a password, or an API key. A
redaction filter additionally blanks any log line that happens to mention
`password`, `token`, `secret`, or `api_key` as a backstop.

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

Set `ENABLE_REQUEST_LOGGING=false` to silence the per-request line while
still logging startup/shutdown and errors. `LOG_LEVEL` controls overall
verbosity (`DEBUG=true` also raises SQL echo logging).

## 8. Backups

```powershell
# Create a timestamped backup in BACKUP_DIR (./backups by default)
powershell -File scripts\backup_db.ps1
```
```bash
scripts/backup_db.sh
```

Prunes backups older than `BACKUP_RETENTION_DAYS` automatically. Backup
files are never committed (`.gitignore` excludes `/backups/`, `*.sql`,
`*.sql.gz`, `*.dump`). Check what exists without touching the filesystem
yourself via `GET /api/v1/system/backups/status` (admin-only) — it reports
the most recent backup's timestamp and filename, never a download link.

There is no built-in scheduler; run the script manually or wire it into an
external cron / your host's scheduled-jobs feature.

## 9. Restore

**Destructive** — overwrites all data in the target database. Always
confirms before doing anything:

```powershell
powershell -File scripts\restore_db.ps1 -BackupFile .\backups\sales_agent_20260101_120000.sql
```
```bash
scripts/restore_db.sh ./backups/sales_agent_20260101_120000.sql
```

**Rehearsing a restore without destroying real data:** run the backup
script to produce a fresh dump, then restore that *same* dump back into
the *same* database — this exercises the full restore path (container
lookup, confirmation prompt, `psql` invocation, error handling) without
any actual data loss, since the content restored matches what's already
there. To test against genuinely different data, restore into a disposable
second Postgres container instead of the one your app is using.

## 10. Back to Mock

Everything defaults to Mock/Safe Mode. To revert after experimenting with
a real provider, set in `.env` and restart the backend:

```bash
LLM_PROVIDER=mock
EMAIL_INTEGRATION_PROVIDER=mock
REPLY_TRACKING_PROVIDER=mock
```

(`LLM_ENABLE_REAL_CALLS`, `EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS`, and
`REPLY_TRACKING_ENABLE_REAL_READS` can stay as they are — every factory
already refuses a real call unless its provider is also explicitly
selected.) Confirm with `GET /api/v1/system/status` — every
`*_real_*_enabled` field should read `false` and every `*_provider` field
should read `mock`.
