# Beta Onboarding Guide

Compact guide for running this system with a **first real Beta customer**
— safely, explainably, and without automatic sending. Read
[`CUSTOMER_READINESS.md`](./CUSTOMER_READINESS.md) first for the full
go/no-go checklist; this document is the shorter, day-to-day walkthrough.

## What "Beta-ready" means here

- **No automatic sending, ever.** There is no send button and no send
  endpoint anywhere in this system (verified by a standing regression
  test — see `tests/test_deployment_regression.py`).
- **Human Review is mandatory** for every email draft. Do-not-contact is
  checked before every workflow, test run, and dispatch attempt, and can
  never be switched off.
- **Mock/Safe Mode is the default** for every provider (LLM, email
  integration, reply tracking, dispatch). Real providers require two
  independent, explicit opt-ins each — see `.env.example` and
  `docs/PRODUCTION_CHECKLIST.md`.
- **"Beta-ready" is a technical signal, not a legal clearance.** A real
  Beta customer still requires your own legal/compliance sign-off — see
  `CUSTOMER_READINESS.md` and `COMPLIANCE.md`.
- **Use personal data sparingly.** Only store what a given step actually
  needs (e.g. a contact email once Human Review is about to happen) —
  don't import or paste more lead/contact detail than the current step
  requires. See `COMPLIANCE.md` for data-minimization and retention.

## 1. Beta Setup (once per environment)

1. Follow `DEPLOYMENT.md` to get the stack running
   (`docker compose up -d --build`).
2. Log in as an admin account and open **Admin Controls**
   (`/admin/controls`) — confirm every `allow_real_*` toggle is off and
   `dispatch_mode` is `draft_only` unless you have deliberately decided
   otherwise.
3. Open the **Setup Checklist** (same page) — every item should be
   `passed`; `warning`/`blocker` items name exactly what's missing.
4. Optionally seed a small, explainable sample dataset (sample Offer/ICP
   profile + a handful of Mock lead candidates) so a new admin/sales
   account has something to click through immediately:
   ```bash
   python scripts/seed_demo_data.py
   ```
   This only ever calls the existing, already safety-gated API with the
   Mock provider — it never contacts a real company, never sends
   anything, and is safe to re-run.

## 2. Onboarding a new account (per user)

Every logged-in account has its own `/onboarding` walkthrough. As of
Phase 36 it covers, in order: welcome → profile/company setup → Offer/ICP
setup → Safe Mode / provider / compliance / Do-not-contact review → first
Lead Sourcing → first Qualification → first Outreach Queue → first Draft
Review → **first Real-World Test Mode run** → **Feedback & Quality
Dashboard review** → completion. Each step links directly to the page
where it's done and can be marked complete or skipped — nothing here is
enforced server-side beyond what each linked page already enforces.

## 3. First customer run (walkthrough)

1. **ICP/Offer prüfen** — `/sales-strategy/icp` and `/sales-strategy/offers`.
   Confirm at least one active profile of each exists (or use the seeded
   sample ones).
2. **Leads/Candidates importieren oder auswählen** — `/lead-sourcing`:
   start a sourcing run (Mock by default) or import candidates manually,
   then review/approve them.
3. **Real-World Test Mode starten** — `/real-world-test`: pick a Lead
   Candidate (or a direct company name), leave `mode=safe` for the first
   run, and start it. This wraps the existing Sales Workflow — it
   produces CRM records and usually an email draft, but never sends
   anything.
4. **Human Review durchführen** — `/reviews` or the CRM Email Drafts
   list: set the review status, add a comment if useful. Approving a
   draft here **never** sends it.
5. **Feedback/Quality prüfen** — `/quality` (dashboard),
   `/quality/feedback` (give/manage feedback), `/beta-test` (session
   tracking). Give feedback on the draft, the lead quality, the research
   output, the workflow itself, or general/UI feedback — see below.
6. There is no step 7 that sends anything. Any real outreach beyond this
   point is a separate, deliberate, human action outside this system's
   automated scope in this phase.

## 4. Feedback process

`/quality/feedback` accepts feedback tied to: an email draft, a lead
candidate/CRM lead, a company, a workflow run, a **Real-World Test Run**,
an outreach queue item, a dispatch, a reply, a qualification result, or
**general/UI feedback** not tied to any single record (`entity_type:
"general"`, no entity id needed).

Every feedback item has:

- **Rating** (1–5).
- **Feedback Type** (positive/negative/correction/bug/quality_issue/
  compliance_issue/missing_context/wrong_target/bad_copy/good_result).
- **Priority** (low/medium/high) — a triage hint for reviewers only; it
  never changes scheduling or triggers anything automatically.
- **Status** (open/reviewed/accepted/rejected/archived) — only
  admin/reviewer accounts can change this.
- **Kommentar** (free text, length-bounded).
- Optional links to a Real-World Test Run, Lead, Workflow Run, etc., so
  feedback can be traced back to exactly what it's about.
- `is_blocking`: marks feedback as a hard signal — surfaced as a warning
  (and, for Outreach Dispatch, an actual blocker) elsewhere, but it never
  bypasses Do-not-contact or Human Review, and never sends anything by
  itself.

Every feedback create/review/archive action is recorded in the Audit Log
(`/audit-logs`, admin-only) — action, actor, entity, never a secret or a
full draft body.

## 5. Admin checklist (before inviting a Beta customer)

- [ ] Setup Checklist (`/admin/controls`) shows no `blocker`.
- [ ] `GET /api/v1/onboarding/readiness` (or the `/onboarding` page) shows
      at least `beta_testable`, ideally `beta_ready` — remember this is a
      technical signal only.
- [ ] Quality Dashboard (`/quality`) shows at least one scored workflow
      run/draft and zero open **blocking** feedback items.
- [ ] A named person has reviewed `CUSTOMER_READINESS.md` and confirmed
      legal/compliance sign-off for the target jurisdiction.
- [ ] Backups are configured and a restore has been rehearsed (see
      `DEPLOYMENT.md` sections 8–9).
- [ ] The Beta customer has been told, explicitly: no automatic sending,
      Human Review is mandatory, Do-not-contact is enforced, and quality
      scores/"beta-ready" are decision aids, not guarantees.

## 6. Known limitations

- Single-tenant: one workspace per deployment (see
  `CUSTOMER_READINESS.md` → Known Limitations for the full list).
- Feedback is not yet linked to a specific Beta Test Session — session
  summaries reflect system-wide aggregates at completion time, not only
  what happened during that session (see `beta_test_service.py`).
- The seed script's Mock lead pool is small and fixed (8 example
  companies) — enough to demo qualification/review/feedback, not a
  realistic volume test.
- No automated scheduler for backups or data retention runs — both are
  triggered manually or via your own external cron.

## 7. Support / rollback

- **Something looks wrong after a deploy**: check
  `GET /api/v1/system/status` (admin-only) and `docker compose logs -f
  backend` first — both are safe to share (no secrets).
- **Roll back a bad deploy**: redeploy the previous image/commit; the
  database schema is additive-only by default (`init_database()` never
  drops a column) and Alembic migrations are reversible via
  `alembic downgrade -1` (see `DEPLOYMENT.md` section 5) — review what a
  downgrade actually does before running it against real data.
- **Roll back a bad config change**: Admin Controls changes are stored in
  `WorkspaceSettings` and can be reverted from the same page at any time;
  environment variable changes require a restart.
- **Data issue**: see `DEPLOYMENT.md` sections 8–9 for backup/restore.
- **A Beta customer reports a problem**: capture it as feedback
  (`/quality/feedback`, mark `is_blocking=true` if it should block further
  outreach on the affected lead/draft) so it's tracked and auditable
  rather than only discussed verbally.
