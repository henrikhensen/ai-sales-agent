# Project Status

See [`PROJECT_RULES.md`](./PROJECT_RULES.md) for the binding rules
(safety, architecture, process) every phase below follows.

## Current Phase: 39 — Guided Lead Discovery Agent ("Lead Finder")

**Status: implemented. Main benefit: enter a target customer → find
candidates → analyze their websites → review qualified leads → prepare
drafts, all guided in one place. No automatic sending was added.**

Phase 39 adds a guided "Lead Finder" workflow that removes the manual
work of stitching together Lead Sourcing, Website Research, Lead
Qualification, and the Outreach Queue by hand. It is a thin orchestrator
— it introduces no new scraping, scoring, or drafting logic of its own,
reusing the existing services end to end:

- **`LeadDiscoveryService`**
  (`backend/application/lead_discovery/lead_discovery_service.py`, new):
  `create_run` creates an ad-hoc `LeadSourcingCampaign` + `OutreachCampaign`
  under the hood from target customer/region/offer/ICP; `run_pipeline`
  calls the existing `LeadSourcingService.start_run` (find candidates +
  website research + ICP fit, unchanged) then `LeadQualificationService.
  qualify_lead_candidate` per candidate (ICP **and** Offer fit, unchanged)
  and, for qualified candidates, `OutreachQueueService.build_queue`
  (unchanged) to place them in a review queue — it never creates a draft
  itself. `create_drafts_for_qualified_candidates` is a **separate,
  explicit** action that calls the existing `OutreachQueueService.
  prepare_batch` (unchanged) to prepare — never send — an email draft for
  queued items still awaiting one. `add_candidate_to_queue` lets a human
  manually queue one specific candidate that didn't cross the automatic
  score threshold (Do-not-contact/duplicate checks still apply
  unconditionally). `mode` (`safe`/`mock`/`real_llm`, default `mock`)
  mirrors Real-World Test Mode's gate exactly: `real_llm` is refused
  outright unless `LLM_ENABLE_REAL_CALLS` is already set.
- **Website quality, added to the existing Lead Sourcing pipeline**
  (`backend/application/lead_sourcing/lead_sourcing_service.py`
  `assess_website_quality`, `LeadCandidate.website_quality_level`/
  `website_quality_reasons`, new columns): a deterministic, LLM-free
  heuristic (title/meta description present, text length, pages fetched)
  computed from the website research result **already fetched** for ICP
  scoring — no second fetch, no extra cost, identical in Safe/Mock mode.
  Available to every Lead Sourcing candidate, not just Lead Finder ones.
  A fetch failure (invalid/unreachable URL) is classified `"unknown"`
  with a reason, not silently left blank — caught during live
  verification against a real Postgres database (a `.example` mock
  domain correctly fails DNS resolution).
- **Domain**: `LeadDiscoveryRun` entity/repository (table
  `lead_discovery_runs`) storing exactly the requested fields (found/
  analyzed/qualified/rejected/created_drafts counts, warnings, errors,
  mode, status, timestamps, links to the underlying sourcing/outreach
  campaigns) — migration `f3a9c1d8e7b2`.
- **API**: `POST/GET /api/v1/lead-discovery/runs`,
  `GET /api/v1/lead-discovery/runs/{id}` (candidates enriched with
  qualification result + queue/draft status, no client-side joins
  needed), `POST .../run`, `POST .../create-drafts`,
  `POST .../candidates/{id}/add-to-queue`. RBAC: admin/sales create/run/
  draft, admin/sales/reviewer view. No send-capable endpoint anywhere in
  this router.
- **Frontend**: new `/lead-finder` page — "Wen willst du finden?" form
  (Branche/Kundentyp, Ort/Region, Angebot, optionales ICP, Anzahl Leads,
  Mindestscore) → result view per candidate (Website-Qualität + Gründe,
  Fit-/Qualifikations-Score, Warum geeignet/ungeeignet, Draft-Status,
  Review-Status, Warnings) with three actions (Details ansehen, Draft
  prüfen, Zur Review Queue hinzufügen) — no send UI, no send button.
  Made prominent: a banner on the Command Center, the first item after
  Command Center in the Sidebar's "Start" section, and the Command
  Center's "Firma analysieren" journey step now points here (the
  single-company Sales Workflow remains reachable as a secondary link
  in the same card).
- **Tests**: `tests/test_lead_discovery_service.py` (14),
  `tests/test_api_lead_discovery_endpoint.py` (12),
  `tests/test_frontend_lead_finder.py` (9 source-level checks, matching
  this project's no-Jest convention) — cover pipeline orchestration
  against the existing fakes, the real_llm mode gate, do-not-contact
  blocking a candidate before it is ever qualified, the guard against
  re-running a completed pipeline, draft creation staying gated on
  pipeline completion, the manual queue override, and the standing "no
  send-capable endpoint/label" regression checks.

## Prior Phase: 38 — Command Center UX Polish

**Status: implemented. Frontend is more beginner-friendly — no sending
functionality added, no safety rule loosened.**

Phase 38 is a frontend-only UX pass: the previous dashboard
(`frontend/app/page.tsx`) was overloaded (a generic status card, a
6-item quick-access grid, and a 5-agent grid all competing for
attention) and the Sidebar listed ~35 links across 10 flat sections with
no distinction between beginner and admin/advanced tooling. No backend
endpoint, schema, or service changed.

What changed:

- **New Command Center home page** (`frontend/app/page.tsx`, rewritten):
  a prominent, always-visible **Safety Status** card (Safe/Mock Mode,
  kein automatischer Versand, Human Review erforderlich, Do-not-contact
  aktiv, echte Provider nur bewusst aktiv — the last one driven by live
  `OnboardingReadinessChecks` data, the rest are standing product
  guarantees); a **3-work-area layout** (A · Setup, B · Lead prüfen, C ·
  Draft & Review) that nests the **6-step user journey** (Zielkunde/
  Angebot prüfen → Firma/Website analysieren → Lead qualifizieren →
  Draft erstellen → Review durchführen → Outreach Queue vormerken, kein
  Versand) with a per-step status (offen/bereit/erledigt/blockiert)
  derived from existing data (onboarding readiness, workflow runs,
  qualification dashboard, email drafts, outreach dashboard) and one
  clear next-action link per step; a decluttered **Überblick** section
  (letzte Workflows, Leads mit nächstem Schritt, offene Reviews, letzte
  Warnings); and a de-emphasized **"Weitere Werkzeuge"** row for
  agents/CRM-pipeline/quality/settings/admin — nothing was removed, it
  was moved out of the primary flow. No new API calls were introduced;
  every widget reuses an existing endpoint already used elsewhere in the
  app (`getOnboardingReadiness`, `listSalesWorkflowRuns`,
  `getLeadQualificationDashboard`, `listCrmEmailDrafts`,
  `getOutreachDashboard`), fetched via `Promise.allSettled` so a 403 for
  one role never breaks the page.
- **Sidebar simplified** (`frontend/components/layout/Sidebar.tsx`): 10
  flat sections collapsed into 5 — Start, Verkaufen, Postfach,
  Sicherheit, and a single collapsible **"Erweitert"** disclosure
  (native `<details>`, no new dependency) holding every admin/advanced
  route (Workflows overview, Workflow History, Outreach Dispatch,
  Website Research, individual Agents, Quality/Beta/Real-World Test,
  Compliance Documents/Data Retention/Data Requests, Audit Logs, System
  Status, Users, Admin Controls, Settings). Every route that existed
  before still exists — nothing was deleted, only regrouped and
  de-emphasized. "Erweitert" auto-opens when the current page is inside
  it, so a deep link still shows its own position in the nav.
- **Copy improvements**: `/lead-qualification` heading renamed to the
  German "Lead-Qualifikation"; the Sales Workflow result panel
  (`frontend/components/workflows/WorkflowResultSections.tsx`) gained a
  "Gefundene Informationen" label over the Website Research findings and
  its Email Draft section is now titled "Draft zur Prüfung (nur Entwurf,
  kein Versand)"; the header/sidebar branding now reads "AI Sales
  Copilot" consistently.
- **Tests**: `tests/test_frontend_command_center.py` (new, 10 tests) —
  since this frontend has no Jest/RTL (PROJECT_RULES.md: no unnecessary
  new tools) and the Command Center's real content renders client-side
  behind auth, these are source-level regression checks: no
  "Senden"/"Versenden" button label exists anywhere in the frontend
  source, the Command Center contains its required sections/copy and
  all six journey CTAs, the Sidebar's "Start" section stays short while
  every admin/advanced route remains reachable under "Erweitert", and
  no core journey page file was deleted. Complements (does not replace)
  `npx tsc --noEmit` + `npm run build`, both of which stay green.

## Prior Phase: 37 — Final Polish & Launch Checklist

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

- Phase 38: Command Center UX polish
- Phase 37: final polish and launch checklist
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

## Standing Guarantees (apply to every phase, including 39)

- Mock provider is the default everywhere; real providers require
  explicit, separate configuration.
- No automatic email sending, no batch send, no reply-send endpoint, no
  automatic external draft creation.
- Do-not-contact and Human Review are never bypassed by any feature.
- "Approved" / "completed" never means something was sent.
- No secrets, API keys, or tokens are ever logged, committed, or shown in
  the frontend.
