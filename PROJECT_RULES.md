# Project Rules

Binding rules for every phase of this project. Any phase instruction that
conflicts with these must be flagged, not silently followed — these are
the invariants that make the product safe to run against real leads.

## Safety (non-negotiable)

- **No automatic sending.** No feature ever sends an email, message, or
  reply on its own. Every send-shaped action requires a real, external
  provider explicitly enabled *and* a human's final confirmation.
- **No batch/mass send, no auto-dispatch.** Outreach always proceeds one
  reviewed item at a time; there is no "send all" action anywhere.
- **No send-capable endpoint or send button by default.** Regression
  tests assert no API path contains `send`. If a future phase ever adds
  real sending, it must be opt-in, explicitly confirmed per action, and
  never default-on.
- **No automatic external draft creation.** Drafts created in a real
  provider (Gmail/Outlook/etc.) only ever happen via an explicit, human-
  triggered action — never as a side effect of another feature.
- **Do-not-contact is never bypassed.** Every workflow, dispatch, or test
  run that could reach a real contact checks Do-not-contact first and
  blocks on a match, regardless of mode/role/flag.
- **Human Review is never bypassed.** "Approved" or "completed" never
  means something was sent — it only ever means a human may now act.
- **Mock/Safe Mode is the default for every provider** (LLM, email
  integration, reply tracking, outreach dispatch, real-world test mode).
  A real provider requires two independent, explicit opt-ins: selecting
  the provider *and* a separate `*_ENABLE_REAL_*` flag. Missing either
  one must never silently fall back to "real" — it falls back to mock/
  refuses, and says so clearly.
- **Missing critical config fails loudly, not silently unsafe.** In
  production (`APP_ENV=production`), a missing/default critical secret
  (JWT signing key, DB password, CORS origins) must stop the process
  from starting — never serve traffic with an insecure default.
- **No secrets ever leak.** Never commit, log, or return a secret, API
  key, password, or token — not in Git, not in a log line, not in an
  API response, not in the frontend bundle (`NEXT_PUBLIC_*` is public by
  definition; nothing secret goes there). Audit logs and error messages
  name *which* setting is unsafe, never its value.
- **No scraping shortcuts.** No LinkedIn scraping, no scraping behind a
  login/paywall, no CAPTCHA bypass, no guessing personal emails from a
  pattern. Only public pages a caller explicitly supplies a URL for.

## Architecture

- **Clean Architecture, strictly layered:**
  `backend/domain/` (entities as plain dataclasses, repository interfaces
  as ABCs, enums, exceptions) → `backend/application/` (services,
  per-feature Pydantic schemas) → `backend/infrastructure/` (SQLAlchemy
  models/repositories, external provider adapters) → `backend/api/v1/`
  (routes, `dependencies.py` for DI wiring, `router.py` for registration).
  Routes never talk to the database directly; services never import
  FastAPI/SQLAlchemy types.
- **Reuse existing services — no parallel/duplicate implementations.**
  Before adding a new service, check whether an existing one (Sales
  Workflow, Do-not-contact, Offer/ICP, Quality Scoring, Audit Log) already
  does the job; wrap/extend it instead of re-implementing.
- **Repository pattern**: an abstract `*Repository(ABC)` per aggregate in
  `domain/repositories/`, a concrete `SQLAlchemy*Repository` in
  `infrastructure/repositories/`. New optional cross-cutting dependencies
  are added as constructor keyword args defaulting to `None`, so existing
  call sites and tests never break.
- **RBAC**: three roles — `admin`, `reviewer`, `sales`. Every new
  endpoint states explicitly who may call it (`RequireAdminUserDep`,
  `RequireReviewerOrAdminDep`, `RequireSalesOrAdminDep`,
  `RequireSalesReviewerOrAdminDep`, `RequireActiveUserDep`) — never left
  to fall through to "any authenticated user" by omission.
- **Audit everything sensitive.** Every create/block/approve/reject/
  abort/dispatch-relevant action gets an `AuditLogService.record(...)`
  call — action, result, actor, entity, never a secret or a full email/
  LLM-prompt body.
- **No unnecessary new tools/dependencies.** Prefer what's already in
  the stack (FastAPI, SQLAlchemy async, Pydantic, Next.js, the existing
  rate-limit/audit/compliance services) over introducing a new library
  unless the task explicitly calls for it and the gap is real.

## Process

- **Minimal-invasive.** Extend, don't rewrite. A new feature should read
  as an addition to the codebase, not a refactor of unrelated code.
- **No pseudocode, no TODOs, no half-finished code.** Every change must
  be complete and runnable when the phase ends.
- **Tests required, and they must pass before considering a phase done**:
  service-level tests against in-memory fakes, API-level tests for RBAC/
  auth/safety gates, and a regression check that no send-capable
  endpoint exists. Run the full suite, not just the new tests, before
  wrapping up.
- **Existing features must not break.** A new phase is only done once
  the full backend test suite and the frontend type-check/build both
  pass, and the standing regression tests (deployment, security,
  do-not-contact, no-send) still pass unchanged.
- **Docs stay truthful.** If a doc claim (checklist item, README section)
  no longer matches the code, fix the doc in the same phase rather than
  leaving it stale — a wrong "not yet implemented" is worse than no note
  at all.
- **`PROJECT_STATUS.md`** is the running phase log/changelog — update it
  at the end of every phase with what changed and what safety guarantee
  still holds. **`PROJECT_RULES.md`** (this file) only changes when a
  rule itself changes, not on every phase.

## Definition of done, per phase

1. Backend implementation follows the layering above; reuses existing
   services where possible.
2. Frontend (if applicable): typed API client + role-gated page, no send
   UI, disclaimers where the feature could be mistaken for doing more
   than decision support.
3. Tests added and full suite green (`python -m pytest -q` and
   `cd frontend && npm run build`).
4. `docker compose up -d --build` succeeds; `/health`, `/docs`, and the
   frontend login page all respond correctly.
5. `PROJECT_STATUS.md` updated.
6. Changes committed with a clear message and pushed, after `git status`
   confirms nothing unexpected (secrets, unrelated files) is staged.
