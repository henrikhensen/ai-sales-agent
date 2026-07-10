# Deployment Guide

This is a **general orientation guide**, not an automated deployment. It
describes how one *could* later deploy this project to a few common hosting
targets. It intentionally contains:

- **No real credentials or account-specific configuration.**
- **No deployment automation that would incur cost by itself.**
- No commands that were actually run against a cloud provider from this
  repository.

Deploying this project remains a deliberate, human-triggered decision. Read
[`docs/PRODUCTION_CHECKLIST.md`](./PRODUCTION_CHECKLIST.md) first — several
items there (auth, rate limiting, real secrets) should be addressed before
any of this is exposed to real traffic.

## What you're deploying

Two independently deployable pieces, plus two managed data services:

| Component | What it is | Where it could run |
| --- | --- | --- |
| `backend` | FastAPI app (Dockerfile at repo root) | Any container host |
| `frontend` | Next.js app (`frontend/Dockerfile`, standalone build) | Any container host, or a Node/Vercel-style host |
| PostgreSQL | Stateful data store | A managed Postgres add-on (do not self-host on the same box as the app long-term) |
| Redis | Cache / framework dependency | A managed Redis add-on |

Both `Dockerfile`s build standalone, production-ready images already used by
`docker compose up --build`, so most hosts that accept a Dockerfile can run
this without changes beyond environment variables.

## Environment variables to set on any host

Backend (see `.env.example` for the full, documented list):

- `APP_ENV=production`, `DEBUG=false`
- `POSTGRES_*` (or wherever your host injects its managed Postgres connection
  details — you may need to adapt `Settings.database_url` if a host only
  gives you a single connection string)
- `REDIS_*` (same consideration for managed Redis)
- `LLM_PROVIDER=mock` until you deliberately decide to pay for real model
  calls, then `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY`
- `CORS_ALLOWED_ORIGINS=https://your-frontend-domain.example` (exact origin,
  not `*`)

Frontend:

- `NEXT_PUBLIC_API_BASE_URL=https://api.your-domain.example` — set at
  **build time** (see `frontend/Dockerfile`'s `ARG`), since it is inlined
  into the browser bundle.

## Schema setup on a new host

After the backend container can reach Postgres, apply the schema once via
Alembic rather than only relying on the automatic `create_all` the backend
also runs on every startup:

```bash
docker compose exec backend python -m alembic upgrade head
```

See `DEPLOYMENT.md` section 5 for the full explanation, the
`stamp head` alternative for a database that already has the schema, and
how to add new migrations going forward.

## Missing/insecure production secrets fail the startup, not the app's safety

Once `APP_ENV=production` is set, the backend refuses to start at all if
`JWT_SECRET_KEY`/`POSTGRES_PASSWORD` are still development defaults or
`CORS_ALLOWED_ORIGINS` is empty/`*` — check your host's deploy logs if a
production rollout doesn't come up; the error message names exactly which
variable is missing/insecure (never the value itself).

## Option: Render

- Two services: a "Web Service" from the root `Dockerfile` (backend) and a
  second from `frontend/Dockerfile` (frontend), or use Render's native
  Node buildpack for the frontend instead of the Dockerfile.
- Add a Render "PostgreSQL" and "Key Value" (Redis) instance; wire their
  connection details into the backend service's environment variables.
- Render provisions HTTPS automatically on `*.onrender.com` or a custom
  domain.
- Good fit if you want the least infrastructure to manage.

## Option: Railway

- Similar shape to Render: one service per Dockerfile, plus Railway's
  managed Postgres and Redis plugins.
- Railway auto-detects the Dockerfiles; set the build context per service
  (repo root for backend, `frontend/` for frontend).
- Environment variables are set per service in the Railway dashboard.

## Option: Fly.io

- One `fly.toml` per app (backend and frontend), each pointing at its
  Dockerfile (`fly launch` scaffolds this interactively — do not run it
  unattended, it can create billable resources).
- Fly Postgres (`fly postgres create`) or an external managed Postgres.
- Requires the Fly CLI and a Fly account; nothing in this repo assumes Fly is
  used.

## Option: Hetzner VPS (self-managed)

- Provision a VPS, install Docker + the Docker Compose plugin.
- Copy the repo, create a real `.env` on the server (never commit it),
  then run:
  ```bash
  docker compose -f docker-compose.prod.yml --env-file .env up --build -d
  ```
- `docker-compose.prod.yml` already stops publishing Postgres/Redis ports to
  the host and drops the dev bind-mounts/`--reload` — see that file's
  comments.
- Put a reverse proxy (Caddy or nginx) in front for TLS termination and to
  route a domain to the frontend (port 3000) and an API subdomain to the
  backend (port 8000). Caddy is the simplest option (automatic Let's
  Encrypt certificates with a two-line Caddyfile).
- You are responsible for OS patching, firewall rules, and backups on a VPS
  — there is no managed layer here.

## Option: AWS

- Most flexible, most operational overhead. A reasonable shape:
  - **ECS Fargate** (or App Runner for less configuration) running the two
    container images, pushed to **ECR**.
  - **RDS for PostgreSQL** and **ElastiCache for Redis** as the managed data
    services.
  - **ALB** in front for TLS (via **ACM**) and routing.
  - **Secrets Manager** or **SSM Parameter Store** for `ANTHROPIC_API_KEY`
    and database credentials — never bake them into the image or task
    definition in plain text.
- Only sensible once you need AWS-specific integrations or already run other
  infrastructure there — for a project this size, Render/Railway/Fly reach
  production faster with less to operate.

## What this repository does NOT do for you

- It does not create any cloud resources.
- It does not store or assume any provider-specific credentials.
- It does not run `terraform apply`, `fly deploy`, `railway up`, or similar
  from CI — `.github/workflows/ci.yml` only installs dependencies, runs
  backend tests, and builds the frontend.
- It does not decide which provider to use — that's a deliberate,
  cost-bearing decision for a human to make with the checklist in
  `docs/PRODUCTION_CHECKLIST.md` in hand first.
