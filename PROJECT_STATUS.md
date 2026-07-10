# Project Status

## Current Phase: 35 — Production Deployment Finalization

**Status: implemented.**

Phase 35 finalizes production-deployment readiness (config validation,
migrations, docs) — **it does not activate automatic sending, batch
dispatch, or any new automation.** No new service was added to either
compose file; `docker-compose.yml`/`docker-compose.prod.yml` still run
exactly backend, frontend, postgres, redis. Mock/Safe Mode remains the
default for every provider; nothing here changes that.

What was added/changed:

- **Hard-fail production config validation**
  (`backend/shared/production_checks.py:validate_production_config`,
  raises `ProductionConfigError`): when `APP_ENV=production`, the backend
  now **refuses to start** — not just logs a warning — if
  `JWT_SECRET_KEY` or `POSTGRES_PASSWORD` are still their insecure
  development defaults, or `CORS_ALLOWED_ORIGINS` is empty/`*`. Wired
  into `backend/main.py` at module load, before the app is constructed.
  `get_production_warnings()` (used by `GET /api/v1/system/status`) is
  unchanged and still covers `DEBUG=true` as a warning-only case.
- **`APP_ENV` strict validation** (`backend/shared/config.py`): now a
  `field_validator` restricted to exactly
  `development`/`staging`/`production` (case-insensitive) — a typo like
  `prod` previously silently behaved like development (every
  production-only check compares `!= "production"`); it now fails
  Settings construction immediately instead.
- **Alembic migrations** (`alembic.ini`,
  `backend/infrastructure/database/migrations/`): one baseline revision
  (`ea7b17c08f5f_baseline_schema`) captures the full schema exactly as
  `init_database()` already creates it via `CREATE TABLE IF NOT EXISTS`
  — verified with `alembic check` against both a fresh database and this
  project's existing dev database (no drift either way). `init_database()`
  itself is unchanged (still additive-only, still runs on every startup
  for dev/test convenience); Alembic is now the path for real schema
  *changes* going forward (`alembic revision --autogenerate`). See
  `DEPLOYMENT.md` section 5.
- **Docs refreshed to match actual code**: `docs/PRODUCTION_CHECKLIST.md`
  had two stale items — Rate Limiting was marked "not yet implemented"
  (it has been since an earlier phase) and Alembic was marked missing
  (now added) — both corrected. `docs/DEPLOYMENT_GUIDE.md` and
  `DEPLOYMENT.md` gained migration usage instructions and a note on the
  new hard-fail behavior.
- **Tests**: `tests/test_production_config.py` gained 16 new tests
  (`validate_production_config` hard-fail paths, `APP_ENV` validator);
  `tests/test_alembic_config.py` (new, 7 tests) sanity-checks the
  migration setup without touching a database; `tests/test_deployment_
  regression.py` gained 3 checks (no new compose service, the hard-fail
  path never references Do-not-contact/Review, `init_database` stays
  additive-only).

## Prior Phase: 34 — Real-World Test Mode

**Status: implemented.**

Real-World Test Mode lets an admin/sales account run a controlled test
against a real lead/candidate, a real website, and — only when the system
is explicitly configured for it — real LLM output. It is a thin,
auditable wrapper around the existing Sales Workflow; it does not
duplicate Lead Research, Company Intelligence, Personalization, or Email
Draft logic.

**Phase 34 does not enable sending.** There is no send endpoint, no send
button, and no automatic external draft creation anywhere in this phase.
"Completed" only ever means the underlying Sales Workflow finished and
produced CRM records and (usually) an email draft awaiting Human Review
— exactly like running the Sales Workflow directly. Do-not-contact is
checked before every run, regardless of mode, and can never be bypassed.
Approval/completion never means anything was sent.

What was added:

- **Domain**: `RealWorldTestRun` entity + `RealWorldTestRunRepository`
  port (`backend/domain/entities/real_world_test_run.py`,
  `backend/domain/repositories/real_world_test_run_repository.py`).
- **Persistence**: `RealWorldTestRunModel` (table
  `real_world_test_runs`) + `SQLAlchemyRealWorldTestRunRepository`.
- **Service**: `RealWorldTestRunService`
  (`backend/application/real_world_test/real_world_test_run_service.py`)
  — reuses the existing `SalesWorkflowService`, `DoNotContactService`,
  `OfferService`, and `QualityScoreRepository` rather than duplicating
  any of their logic. `mode` (`safe`/`mock`/`real_llm`) only ever governs
  how much of a run may touch real external systems (website fetch, LLM
  provider) — `real_llm` is refused outright (never silently downgraded)
  unless `LLM_ENABLE_REAL_CALLS=true` is already set.
- **API**: `POST/GET /api/v1/real-world-test-runs`,
  `GET /api/v1/real-world-test-runs/{id}`,
  `POST /api/v1/real-world-test-runs/{id}/abort`. RBAC: admin/sales can
  start a run, admin/sales/reviewer can view, admin-only can abort.
- **Frontend**: `/real-world-test` page — start a run against an existing
  Lead Candidate, CRM Lead, or a direct company name; pick an optional
  ICP/Offer profile; pick a mode (default `safe`); view past runs with
  status, warnings, errors, linked Quality Score, and the raw
  input/result snapshot. No send UI anywhere on this page.
- **Tests**: `tests/test_real_world_test_run_service.py` (12 tests),
  `tests/test_api_real_world_test_endpoint.py` (10 tests) — cover safety
  gates (do-not-contact block, `real_llm` mode gate), RBAC, abort state
  machine, and the standing "no send-capable endpoint" regression check.

## Prior Phases (changelog)

- Add real-world test mode
- Add beta feedback loop and quality scoring
- Add compliance pack and data retention controls
- Fix audit logging for blocked actions
- Add customer onboarding and admin controls
- Add controlled outreach dispatch
- Add outreach campaign queue
- Add lead qualification scoring engine
- Add lead sourcing engine
- Add ICP and offer strategy profiles
- Add compliance hardening, audit logs, and demo polish
- Add deployment monitoring and backup readiness
- Add reply inbox and tracking
- Add safe Gmail/Outlook draft integration
- Add do-not-contact compliance system
- Enable safe real LLM provider mode
- Add CRM pipeline (backend + frontend)
- Add website research (backend + frontend), integrated into Sales Workflow
- Add LLM provider settings (backend + frontend)
- Add role-based access control (backend + frontend)
- Add authentication (backend + frontend)
- Add Human Review (backend + frontend)
- Add CRM integration for Sales Workflows (backend + frontend)
- Add Workflow History (backend + frontend)
- Add Sales Workflow (backend + frontend)
- Add production deployment scaffolding
- Add frontend dashboard
- Add agents: Lead Research, Company Intelligence, Personalization,
  Email Draft, Reply Analysis
- Add core CRM data model with Clean Architecture layers
- Initial Clean Architecture backend scaffold and project setup

## Standing Guarantees (apply to every phase, including 35)

- Mock provider is the default everywhere; real providers require
  explicit, separate configuration.
- No automatic email sending, no batch send, no reply-send endpoint, no
  automatic external draft creation.
- Do-not-contact and Human Review are never bypassed by any feature.
- "Approved" / "completed" never means something was sent.
- No secrets, API keys, or tokens are ever logged, committed, or shown in
  the frontend.
