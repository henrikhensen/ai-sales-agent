# Customer Readiness

This document is a checklist for a human to work through deliberately
before letting a real customer (internal team, design partner, or paid
beta user) touch this system for real outreach. Nothing in this checklist
is enforced automatically by the code — the app's Admin Controls and
Onboarding Readiness check (`GET /api/v1/onboarding/readiness`) surface
*technical* signals only (offer/ICP present, safe mode active, audit logs
on, ...). None of that constitutes legal, compliance, or contractual
clearance. **Real outreach to real people is your responsibility, governed
by your own legal review — not by this checklist.**

See also [`docs/PRODUCTION_CHECKLIST.md`](docs/PRODUCTION_CHECKLIST.md) for
infrastructure/deployment readiness, [`BETA_ONBOARDING.md`](BETA_ONBOARDING.md)
for the day-to-day first-customer walkthrough (setup, sample data,
feedback process), and the README sections "Customer Onboarding und Admin
Controls" and "Controlled Outreach Dispatch" for how the underlying
features work.

## Customer Setup

- [ ] At least one active Offer Profile exists (`/sales-strategy/offers`).
- [ ] At least one active ICP Profile exists (`/sales-strategy/icp`).
- [ ] The user has walked through `/onboarding` and understands the
      intended flow: Offer & ICP → Lead Sourcing → Lead Qualification →
      Outreach Queue → Draft preparation → Human Review → (optional)
      external draft.
- [ ] The user understands that `approved` never means "sent" anywhere in
      this system (Sales Workflow, Outreach Queue, Controlled Dispatch).
- [ ] The user has read the Safe Mode disclaimers on `/onboarding`,
      `/outreach`, `/outreach/dispatch`, and `/admin/controls`.
- [ ] `GET /api/v1/onboarding/readiness` returns at least `demo_ready`.

## Required Admin Controls

Checked via `/admin/controls` (admin-only) or
`GET /api/v1/admin/controls`:

- [ ] `require_human_review` is `true` (this can never be turned off
      through the API — verify it stayed `true` after any control change).
- [ ] `require_do_not_contact_check` is `true` (same — never turnable off).
- [ ] `allow_real_dispatch` is `false` unless a deliberate, reviewed
      decision was made to enable real sending — and even then, real
      sending only ever works through the mock provider or a provider you
      have separately implemented; Gmail/Outlook never implement real send
      in this codebase.
- [ ] `dispatch_mode` is `draft_only` unless `manual_send` was deliberately
      chosen **and** `OUTREACH_DISPATCH_ENABLE_REAL_SEND` is explicitly set
      in the environment (the API rejects `manual_send` outright otherwise).
- [ ] Workspace branding fields (`workspace_name`, `company_name`,
      `default_language`, `default_tone`) reflect the real customer, not
      placeholder demo data.

## Legal/Compliance Pack Checklist

- [ ] `COMPLIANCE.md` has been read by whoever owns legal/compliance for
      this deployment.
- [ ] Compliance Documents (`/compliance/documents` or
      `GET /api/v1/compliance/documents`) have been reviewed — every
      document is a template/notice, not ready-to-publish legal text.
- [ ] `GET /api/v1/compliance/status` shows `legal_review_required: true`
      (always true — a standing reminder, not a togglable setting).

## Data Retention Checklist

- [ ] `DATA_RETENTION_ENABLED` reflects a deliberate decision (default
      `false`).
- [ ] If enabled, at least one Data Retention Policy exists
      (`/compliance/data-retention`) — Onboarding Readiness warns if
      retention is enabled with zero policies.
- [ ] Every policy's `action` has been deliberately chosen — `anonymize`
      is the safe default; `delete` and `archive` are only available for
      entity types whose repository supports them.
- [ ] A dry run has been run and reviewed before any real run.
- [ ] Anyone who can trigger a real run understands it requires explicit
      confirmation and cannot be undone.
- [ ] Confirmed: active do-not-contact entries are never affected by any
      retention run, regardless of age.

## Data Export Checklist

- [ ] `POST /api/v1/compliance/data-export` is admin-only and understood
      to be a read-only search — it never changes, deletes, or sends
      anything.
- [ ] Anyone with admin access understands an export may contain personal
      data and must only be used for an authorized, legitimate purpose
      (e.g. responding to a data subject request).
- [ ] Confirmed (e.g. via `tests/test_data_export_service.py`): no export
      ever contains a secret, API key, or token.

## Data Subject Request Checklist

- [ ] The team knows where to record a data subject request
      (`/compliance/data-requests`, admin-only).
- [ ] Everyone understands recording a request never performs the
      requested action automatically, and never emails the subject.
- [ ] The process for completing a `do_not_contact`-type request (which
      creates a do-not-contact entry automatically on completion) is
      understood by whoever handles these requests.
- [ ] Delete/anonymize requests are handled via Data Retention Policies
      (admin, with explicit confirmation) — `prepare-anonymize` only ever
      previews matching records, it never changes data itself.

## Safety Defaults

These hold without any admin action and should be spot-checked, not
assumed:

- [ ] `LLM_PROVIDER=mock` unless `LLM_ENABLE_REAL_CALLS=true` was
      deliberately set (real Anthropic calls cost money).
- [ ] `EMAIL_INTEGRATION_PROVIDER=mock` unless
      `EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS=true` was deliberately set.
- [ ] `REPLY_TRACKING_PROVIDER=mock` unless
      `REPLY_TRACKING_ENABLE_REAL_READS=true` was deliberately set.
- [ ] `OUTREACH_DISPATCH_MODE=draft_only` and
      `OUTREACH_DISPATCH_ENABLE_REAL_SEND=false` unless real dispatch was a
      deliberate, reviewed decision.
- [ ] `AUDIT_LOGS_ENABLED=true`.
- [ ] `RATE_LIMIT_ENABLED=true`.
- [ ] No send endpoint, batch-send endpoint, or reply-send endpoint exists
      anywhere in the API (`grep -rn "send" backend/api/v1/routes/` should
      only surface documentation/comments, never a route).
- [ ] Do-not-contact and Human Review are re-verified immediately before
      every Sales Workflow / Outreach Queue / Dispatch action — confirmed
      by the automated test suite (`tests/test_*_service.py`,
      `tests/test_api_*_endpoint.py`).
- [ ] Blocked security actions stay auditable: a rejected admin control
      change, a blocked dispatch confirmation, and a do-not-contact-blocked
      review approval each still persist their audit entry even though the
      request that describes them is itself rejected (verified live against
      Postgres, not just against the in-memory test doubles — see
      `AuditLogService.record_independent` and
      `ReviewEventRepository.create_independent`).
- [ ] Audit logs never store secrets, API keys, tokens, full email bodies,
      or full LLM prompts — enforced by `_sanitize_metadata` in
      `backend/application/audit/audit_log_service.py`, including for the
      independently-persisted blocked-action entries above.

## Before First Customer Demo

- [ ] `docker compose up --build` runs cleanly; health endpoint and Swagger
      are reachable.
- [ ] Onboarding Readiness is at least `demo_ready`.
- [ ] Setup Checklist (`/admin/controls` or
      `GET /api/v1/admin/setup-checklist`) has no `blocker` items.
- [ ] A full walkthrough (Lead Sourcing → Qualification → Outreach Queue →
      Draft preparation → Review → optional external draft in mock mode)
      has been run once end-to-end without errors.
- [ ] Everyone attending the demo understands: this is a decision-support
      and drafting tool, not an autosend system.

## Before First Paid Beta

Everything in "Before First Customer Demo", plus:

- [ ] Onboarding Readiness is at least `internal_ready` (ideally
      `beta_ready` — remember this is a technical signal only, see the
      disclaimer above).
- [ ] A named person has legal/compliance sign-off for real outreach in
      the target jurisdiction(s), including applicable email marketing law
      (e.g. GDPR/ePrivacy, CAN-SPAM, CASL) — this system does not verify
      legal basis for contact, only opt-out/do-not-contact status.
- [ ] If any real provider (`LLM_ENABLE_REAL_CALLS`,
      `EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS`,
      `REPLY_TRACKING_ENABLE_REAL_READS`, `OUTREACH_DISPATCH_ENABLE_REAL_SEND`)
      is enabled, its cost/quota implications are understood and budgeted.
- [ ] Backups are enabled (`ENABLE_BACKUPS=true`) with a tested restore
      procedure (see `docs/PRODUCTION_CHECKLIST.md`).
- [ ] A real, rotated `JWT_SECRET_KEY` and database credentials are in
      place (never the `.env.example` placeholder values).
- [ ] Do-not-contact entries from any prior outreach (if migrating from
      another tool) have been imported before the first real send.
- [ ] Legal/Compliance Pack, Data Retention, Data Export, and Data Subject
      Request checklists above are all complete.
- [ ] A named process exists for handling a real data subject request
      (export/delete/anonymize/do-not-contact/correction) within your
      applicable legal deadlines.

## Quality Score / Feedback Loop / Beta Test Session Readiness

Quality Scores and Feedback are decision support only — never a
guarantee, never a substitute for Human Review or Do-not-contact, and
"beta_ready" (both the general Onboarding Readiness signal and the
Quality Dashboard's own `beta_readiness_level`) is a technical signal
only, never a legal clearance.

- [ ] `QUALITY_SCORING_ENABLED=true` and `QUALITY_FEEDBACK_ENABLED=true`
      (see `GET /api/v1/quality/status`).
- [ ] At least one Sales Workflow run and email draft have been scored
      (`GET /api/v1/quality/dashboard` shows a non-null average draft/
      workflow quality score) — an empty dashboard means nothing has been
      evaluated yet, not that quality is good.
- [ ] Average draft/workflow quality score meets or exceeds
      `QUALITY_MIN_DRAFT_SCORE` / `QUALITY_MIN_WORKFLOW_SCORE` before
      inviting a beta customer.
- [ ] Zero open **blocking** feedback items
      (`blocking_feedback_items` on `GET /api/v1/quality/dashboard`) —
      treat any open blocking feedback as a hard go/no-go gate, not a
      warning to note and proceed past.
- [ ] If `QUALITY_REQUIRE_HUMAN_FEEDBACK_FOR_BETA=true`, at least one
      piece of human feedback has been reviewed — a system with zero human
      feedback has not actually been beta-tested by a person yet.
- [ ] If using at least one Beta Test Session
      (`/beta-test`), it has been completed and its summary
      (workflows tested, drafts reviewed, blockers, bugs) reviewed by a
      named person before inviting a real beta customer.
- [ ] Legal/compliance sign-off above is still required regardless of
      quality score or beta readiness level — a high quality score never
      substitutes for legal clearance, Do-not-contact, or Human Review.

## Known Limitations

- Single-tenant only: `WorkspaceSettings` is a single row, not per-customer
  multi-tenancy. Running multiple distinct customers on one deployment
  requires separate deployments today.
- No built-in user invite flow: admins manage roles through the existing
  `/users` overview (admin-only); there is no self-service signup-with-
  invite-code system.
- Real sending is intentionally unimplemented for Gmail/Outlook — no send
  scope (`gmail.send`/`Mail.Send`) is ever requested. `manual_send` mode
  only ever produces a real outcome through the mock provider or a
  provider you add yourself.
- Onboarding Readiness and the Setup Checklist are structural/technical
  checks only — they cannot and do not assess message content quality,
  target-market legal basis for contact, or deliverability reputation.
- No automated data-retention/purge job exists yet for audit logs
  (`AUDIT_LOG_RETENTION_DAYS` is informational only in this phase).
- Data Retention runs scan up to 5,000 records per entity type per run
  (paginated) rather than an unbounded full-table scan — for very large
  tables, a single run may need to be started again to cover the rest.
- Data Retention's `entity_type="lead"` operates on `Contact` records
  (name/email/phone) — the CRM `Lead` entity itself carries no personal
  data. `entity_type="audit_log"` is count-only in a real run; audit logs
  are never deleted or anonymized, by design.
- No automated scheduling for Data Retention runs exists — every real run
  is started manually by an admin.
- Quality Scoring is rule-based by default and, even with
  `QUALITY_SCORING_USE_LLM=true`, only ever assists the rule-based score —
  it does not verify factual claims, cannot detect every compliance risk,
  and is not a substitute for a human reviewing the actual draft/reply.
- Beta Test Sessions summarize the system-wide quality score/feedback
  aggregate at the moment a session is completed — Quality Scores and
  Feedback are not currently linked to a specific session, so a session's
  numbers reflect overall system activity, not only what happened during
  that session's timeframe.
- `QualityScoreRepository.list_all_latest()` (used by the Quality/Beta
  dashboards) scans a bounded, newest-first page rather than a true SQL
  `DISTINCT ON` query — adequate at this project's scale, but a very high
  volume of scores could mean the dashboard's "latest per entity" set
  misses older entities that haven't been rescored recently.
