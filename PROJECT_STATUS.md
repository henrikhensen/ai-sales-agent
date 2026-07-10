# Project Status

See [`PROJECT_RULES.md`](./PROJECT_RULES.md) for the binding rules
(safety, architecture, process) every phase below follows.

## Current Phase: 37 — Final Polish & Launch Checklist

**Status: implemented. Launch Ready — no automatic sending activated, no
safety rule loosened.**

Phase 37 is a stabilization/polish pass, not a feature phase: a targeted
review of Auth/RBAC, Admin Controls, Safe Defaults, Provider Settings,
Do-not-contact, Human Review, Outreach Queue/Dispatch, Reply Tracking,
Real-World Test Mode, Beta Package, Audit Logs, Data Retention, and
Deployment/Health/Backups, followed by minimal-invasive fixes and a new
compact launch checklist.

What was found and fixed:

- **`QUEUE_STATUS_TONE`** (`frontend/app/outreach/page.tsx`) was missing
  3 of the 15 valid `OutreachQueueStatus` values
  (`sent_manually_confirmed`, `failed`, `cancelled`) — these queue items
  rendered with an incorrect neutral badge instead of their correct
  positive/negative tone. Fixed by adding the three missing entries.
- **`RESULT_TONE`** (`frontend/app/audit-logs/page.tsx`) was missing 2 of
  the 7 real audit-log result values actually written by the backend
  (`duplicate`, from lead sourcing; `cancelled`, from dispatch
  cancellation) — same class of bug, same fix pattern.
- Every other `Record<string, BadgeTone>`-style status/tone map in the
  frontend (outreach dispatch, lead qualification, lead sourcing,
  onboarding/dashboard readiness, quality/feedback, real-world-test,
  replies, data-requests, data-retention, beta-test, sales-strategy) was
  cross-checked against its backend `Literal` source of truth and found
  complete — no further gaps.
- Admin Controls, Provider Settings (`/settings`), RBAC gating, and
  Sidebar navigation links were spot-checked; no broken links, RBAC
  mismatches, or secret-displaying UI found.

What was added:

- **`LAUNCH_CHECKLIST.md`** (new, repo root): a compact, 11-section
  go/no-go checklist (env/secrets, migrations, health checks, test
  users, safe defaults, provider configuration, DNC/Human Review,
  backup/restore, monitoring/logs, rollback path, no-auto-send)
  cross-referencing the existing detailed docs (`docs/
  PRODUCTION_CHECKLIST.md`, `CUSTOMER_READINESS.md`,
  `BETA_ONBOARDING.md`, `DEPLOYMENT.md`) rather than duplicating them.
  Linked from `README.md`.
- **`tests/test_launch_safety_verification.py`** (new, 11 tests): one
  consolidated, readable file asserting the nine standing safety
  guarantees (no send endpoint anywhere, no batch/bulk send under
  dispatch, no reply-send endpoint, external draft creation requires an
  explicit authenticated call, confirming a dispatch requires an actor
  and is never automatic, Do-not-contact/Human Review endpoints are
  registered and auth-gated, audit log metadata sanitization drops
  secret-like keys entirely, every provider defaults to mock, data
  retention defaults to dry-run/anonymize). Complements — does not
  replace — the deeper per-feature tests already in `test_deployment_
  regression.py` and the individual `test_api_*_endpoint.py` files.

No production code, schema, or migration changed in this phase — every
change is either a frontend badge-tone fix, a new doc, or a new test
file.

## Prior Phase: 36 — First Customer Beta Package

**Status: implemented. Beta-ready — no automatic sending activated.**

Phase 36 packages the existing Admin/Compliance/Onboarding/Quality/Audit/
Workflow/CRM/Deployment features into a coherent first-customer Beta
experience: a guided onboarding walkthrough that now ends at Real-World
Test Mode and the Quality/Feedback Dashboard, a seedable sample dataset,
richer feedback (priority, general/UI feedback, Real-World Test Run
linkage), and a compact `BETA_ONBOARDING.md` guide. **It activates no
automatic sending, no batch dispatch, and no new external contact
capability** — every new piece is either a thin extension of an existing,
already-safety-gated service, or documentation/UI around it.

What was added/changed:

- **Onboarding**: two new steps, `first_real_world_test` and
  `feedback_quality_review`, added to `ONBOARDING_STEP_ORDER` (after
  `first_draft_review`, before `completion`) — linking to `/real-world-
  test` and `/quality/feedback` respectively. Existing steps and their
  behavior are unchanged; older in-progress `OnboardingStatus` rows just
  gain two more not-yet-completed steps.
- **Admin Setup Checklist**: new `quality_feedback` item reusing
  `settings.quality_scoring_enabled`/`quality_feedback_enabled` — warns
  (never blocks) if either is off.
- **Feedback, extended** (`UserFeedback` entity/table, migration
  `ea4064e30555`): a new `priority` field (low/medium/high, a triage hint
  only — never changes scheduling or automated behavior), a new
  `real_world_test_run_id` link, `entity_id` is now nullable, and a new
  `entity_type="general"` value for feedback not tied to any single
  record (UI/App-level feedback). `CreateQualityFeedbackRequest` requires
  `entity_id` unless `entity_type="general"`. Fully backward compatible —
  every existing feedback row/caller is unaffected.
- **Sample data seed script** (`scripts/seed_demo_data.py`): calls the
  existing, already safety-gated HTTP API (never the database directly)
  to create a sample Offer Profile, ICP Profile, Lead Sourcing Campaign,
  and start one Mock sourcing run — idempotent-ish, safe to re-run, never
  contacts a real company.
- **Frontend**: `/quality/feedback` gained a priority selector, a
  "general/UI" entity type option (no entity id required), a Real-World
  Test Run ID field, and reads `entity_type`/`entity_id`/
  `real_world_test_run_id` from the URL query string so the new "Feedback
  zu diesem Test Run geben" link on `/real-world-test` pre-fills the
  form. `/onboarding` shows the two new steps and an extended safety
  disclaimer (real providers only via explicit activation, quality scores
  are decision aids, use personal data sparingly).
- **Docs**: new `BETA_ONBOARDING.md` (setup, per-user onboarding, first
  customer walkthrough, feedback process, admin checklist, known
  limitations, support/rollback); cross-referenced from `README.md`,
  `CUSTOMER_READINESS.md`, and `DEMO.md` (new section 26).
- **Tests**: `tests/test_feedback_service.py` (+7),
  `tests/test_api_quality_endpoint.py` (+7),
  `tests/test_onboarding_service.py` (+2),
  `tests/test_admin_controls_service.py` (+2),
  `tests/test_deployment_regression.py` (+3) — cover priority defaults/
  filtering, general feedback validation, Real-World Test Run linkage,
  the new onboarding steps, the new checklist item, and the standing
  "no send capability introduced" checks.

## Prior Phase: 35 — Production Deployment Finalization

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

- Phase 36: first customer beta package
- Phase 35: production deployment finalization
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

## Standing Guarantees (apply to every phase, including 37)

- Mock provider is the default everywhere; real providers require
  explicit, separate configuration.
- No automatic email sending, no batch send, no reply-send endpoint, no
  automatic external draft creation.
- Do-not-contact and Human Review are never bypassed by any feature.
- "Approved" / "completed" never means something was sent.
- No secrets, API keys, or tokens are ever logged, committed, or shown in
  the frontend.
