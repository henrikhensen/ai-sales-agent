# Production Checklist

This project is currently prepared for production **readiness**, not
deployed to production. Nothing in this checklist has been actioned
automatically — it is a checklist for a human to work through deliberately,
with real infrastructure decisions and real costs attached to several items.

Use this alongside [`docs/DEPLOYMENT_GUIDE.md`](./DEPLOYMENT_GUIDE.md).

## Secrets

- [ ] Generate a real `ANTHROPIC_API_KEY` only when ready to pay for real LLM
      calls; keep `LLM_PROVIDER=mock` until then.
- [ ] Store secrets in your host's secret manager (Render/Railway/Fly env
      vars, AWS Secrets Manager, Hetzner + a vault), never in the repo.
- [ ] Rotate `POSTGRES_PASSWORD` away from the example value in `.env.example`.
- [ ] Confirm `.env` (and any `.env.local`) are gitignored and were never
      committed — check with `git log --all --full-history -- .env`.
- [ ] Set a strong, unique value per environment (dev/staging/prod) — never
      reuse the same database password or API key across environments.

## Database (PostgreSQL)

- [ ] Move off the Docker Compose `postgres` service to a managed instance
      (see deployment guide) with automated patching.
- [ ] Enable automated backups with a tested restore procedure.
- [ ] Enforce TLS for database connections in production.
- [ ] Introduce Alembic (or equivalent) migrations before the schema changes
      again — `init_database()` currently does `CREATE TABLE IF NOT EXISTS`,
      which has no rollback and no migration history.
- [ ] Set connection pool limits appropriate to your host's plan.

## Redis

- [ ] Move to a managed Redis instance if the deployment target doesn't
      provide one natively.
- [ ] Enable authentication (`requirepass` / managed equivalent) — the
      current local Redis has none.
- [ ] Decide on persistence requirements (Redis is not yet used for anything
      stateful beyond the framework wiring at this phase).

## CORS

- [ ] Set `CORS_ALLOWED_ORIGINS` to the exact production frontend origin(s)
      only — never `*`. The backend logs a startup warning if `APP_ENV=production`
      and the origin list still contains `*`.
- [ ] Re-verify the CORS origin list every time a new frontend domain
      (staging, preview deployments) is added.

## Authentication & Authorization

- [x] Local JWT authentication with three roles (admin/sales/reviewer) is
      implemented — every API endpoint and frontend page enforces it. See
      the README's "Authentication" and "Roles & Permissions" sections.
- [ ] Decide on multi-tenancy boundaries if this serves more than one sales
      org (currently single-tenant: all data is visible to every
      authenticated account regardless of role).

## Rate Limiting

- [ ] **Not yet implemented.** Add rate limiting in front of the agent
      endpoints before enabling a real (paid) LLM provider, to bound API
      cost and abuse risk.
- [ ] Consider limits both per-IP (unauthenticated abuse) and per-account.

## Backups

- [x] `scripts/backup_db.ps1` / `scripts/backup_db.sh` create timestamped
      `pg_dump` backups and prune old ones (`BACKUP_RETENTION_DAYS`).
      `scripts/restore_db.ps1` / `scripts/restore_db.sh` restore one, with
      an explicit confirmation prompt.
- [x] `GET /api/v1/system/backups/status` (admin-only) reports backup
      configuration and the most recent backup's timestamp/filename — no
      download endpoint.
- [ ] There is no built-in scheduler — wire the backup script into an
      external cron / your host's scheduled-jobs feature for production.
- [ ] Rehearse a real restore drill against a disposable database before
      go-live (see `DEPLOYMENT.md` section 9 for a non-destructive rehearsal
      procedure).

## Logging

- [x] Structured stdout logging is implemented (`backend/shared/logging.py`),
      captured automatically by any container log driver.
- [x] Per-request access logging with a request id, method, path, status,
      duration, and (when decodable from the JWT) user id — gated by
      `ENABLE_REQUEST_LOGGING` (default on). Never logs bodies, passwords,
      tokens, or API keys.
- [ ] Ship logs to a central place (hosting provider's log viewer, or an
      external sink) — stdout alone disappears when a container restarts.
- [ ] Confirm `DEBUG=false` in production (verbose/SQL-echo logging must stay
      off) — the backend now warns at startup and via `GET
      /api/v1/system/status` if this is still `true` while `APP_ENV=production`.

## Monitoring

- [x] `GET /health` / `GET /api/v1/health` (liveness) and `GET /ready` /
      `GET /api/v1/ready` (readiness — 503 when Postgres or Redis is
      unreachable) are implemented. Point uptime monitoring (UptimeRobot,
      Better Uptime, host-native health checks) at these.
- [x] `GET /api/v1/system/status` (admin-only) reports app/provider/safe-mode
      status and any active production warnings, without ever exposing a
      secret.
- [x] `GET /api/v1/metrics` (admin-only, gated by `ENABLE_METRICS`) provides
      simple JSON counters (requests, errors, avg response time, entity
      counts) — intentionally not a Prometheus integration.
- [ ] Add basic resource monitoring (CPU/memory) via your hosting provider's
      dashboard.

## Error Tracking

- [ ] **Not yet implemented.** Unhandled exceptions are logged server-side
      (`backend/main.py`'s global exception handler) but not forwarded
      anywhere external. Consider Sentry or an equivalent before production
      traffic.

## Domain

- [ ] Point a real domain at the frontend; point an API subdomain (e.g.
      `api.yourdomain.com`) at the backend.
- [ ] Update `NEXT_PUBLIC_API_BASE_URL` and `CORS_ALLOWED_ORIGINS` to match.

## HTTPS

- [ ] Terminate TLS at your hosting provider's edge/load balancer (Render,
      Railway, Fly.io all do this automatically; a Hetzner VPS needs a
      reverse proxy such as Caddy or nginx + Let's Encrypt).
- [ ] Ensure the frontend never calls the backend over plain HTTP once a
      domain is live.

## Datenschutz (Privacy / GDPR)

- [ ] Confirm what lead/company/contact data is stored and for how long.
- [ ] Add a privacy policy covering AI-assisted processing of lead data if
      operating in the EU or serving EU customers (GDPR).
- [ ] Confirm the LLM provider's data-processing terms (Anthropic's DPA) are
      acceptable for the data you send it once `LLM_PROVIDER=anthropic` is
      enabled.
- [ ] Provide a data deletion path for leads/contacts on request.

## E-Mail Compliance

- [ ] This system does **not** send email automatically today (by design —
      the Email Draft Agent only produces drafts). If automated sending is
      ever added, it must comply with CAN-SPAM / GDPR / local anti-spam law:
      opt-out handling, sender identification, no purchased lists, etc.
- [ ] Keep the human-approval step for every outgoing email even after any
      future sending feature is added.

## Human-in-the-loop Approval

- [x] Every agent (Lead Research, Company Intelligence, Personalization,
      Email Draft, Reply Analysis) is analysis/draft-only by design — none
      of them contact anyone, send email, or book meetings automatically.
- [ ] When a future phase adds an actual send/contact action, keep an
      explicit human "approve and send" step — do not silently automate it.

## Cloud Hosting Options

See [`docs/DEPLOYMENT_GUIDE.md`](./DEPLOYMENT_GUIDE.md) for a comparison of
Render, Railway, Fly.io, a Hetzner VPS, and AWS.
