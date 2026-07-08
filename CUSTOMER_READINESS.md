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
infrastructure/deployment readiness, and the README sections "Customer
Onboarding und Admin Controls" and "Controlled Outreach Dispatch" for how
the underlying features work.

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
