# Compliance Pack

**This is not legal advice.** Nothing in this document, or anywhere in
this codebase, constitutes legal advice, and nothing here is a
certification that this system is compliant with GDPR, CCPA, CAN-SPAM, or
any other law or standard. This document exists to make the system
**prepared for a legal/compliance review** — not to substitute for one.
Real customer-facing use requires your own qualified legal review. See
also [`CUSTOMER_READINESS.md`](CUSTOMER_READINESS.md) and
[`docs/PRODUCTION_CHECKLIST.md`](docs/PRODUCTION_CHECKLIST.md).

## Scope of this system

AI Sales Agent is a decision-support and drafting tool for B2B sales
outreach preparation: research, personalization, qualification, and
review of email drafts. It is not a marketing automation platform and
does not perform bulk/automatic outreach.

### What this system does

- Researches companies/leads from provided or publicly available data.
- Scores and qualifies leads/candidates against an ICP and Offer profile.
- Drafts personalized emails for a human to review.
- Optionally creates a single external draft (Gmail/Outlook) after an
  explicit, manual action — never sent automatically.
- Reads and stores inbound replies (never answers them automatically).
- Tracks do-not-contact (opt-out) entries and blocks outreach preparation
  and review approval for any match.
- Records an audit trail of security-relevant actions.
- Supports declared data retention policies (dry-run by default),
  cross-entity data export, and tracked data subject requests.

### What this system deliberately does not do

- **No automatic or mass email sending.** There is no send endpoint,
  batch-send endpoint, or reply-send endpoint anywhere in the API.
  "Approved" means a human has internally reviewed a draft — never that
  it was sent.
- **No automatic contact-making** of any kind.
- **No LinkedIn scraping**, no scraping behind a login wall, and no
  CAPTCHA bypassing.
- **No guessing of personal email addresses** — only publicly listed or
  explicitly provided contact information is used.
- **No bypass of do-not-contact or Human Review**, under any
  configuration or role.

## Safe defaults

- Mock providers are the default for LLM, email integration, and reply
  tracking — no real API calls, no real cost, no real mailbox touched.
- Real providers only activate with an explicit `*_ENABLE_REAL_CALLS` /
  `*_ENABLE_REAL_DRAFTS` / `*_ENABLE_REAL_READS` /
  `OUTREACH_DISPATCH_ENABLE_REAL_SEND` environment flag.
- Do-not-contact and Human Review are non-negotiable — they cannot be
  disabled through Admin Controls, regardless of role.
- `DATA_RETENTION_ENABLED=false` by default; a real (non-dry-run)
  retention run anonymizes rather than deletes by default, and always
  requires an explicit admin confirmation.

## Data processed

| Data kind | Examples | Where |
| --- | --- | --- |
| Company data | name, domain, industry | `Company` |
| Contact/lead data | first/last name, email, phone | `Contact`, `LeadCandidate` |
| Email drafts | subject, body (never sent) | `EmailDraft`, `ExternalEmailDraft` |
| Inbound replies | from/to address, subject, body | `Reply` |
| Workflow history | research/personalization payloads | `WorkflowRun` |
| Opt-out records | email/domain/company name, reason | `DoNotContactEntry` |
| Audit trail | actor, action, result, sanitized metadata | `AuditLog` |
| Outreach state | queue items, dispatch attempts (mock/draft-only) | `OutreachQueueItem`, `OutreachDispatch` |

## Data sources

- Data provided directly by the operator (manual entry, imports).
- Publicly available company/website information (Website Research
  agent) — never behind a login, never via CAPTCHA bypass.
- Inbound replies from connected mailboxes (only when a real email
  integration provider is explicitly enabled).

## Data processing

- LLM calls (when real calls are enabled) send lead/company context to
  the configured provider (e.g. Anthropic) to generate research,
  personalization, and draft content.
- Email integration (when real drafts are enabled) creates a draft in
  the connected Gmail/Outlook account — never sends it.
- Reply tracking (when real reads are enabled) reads and stores inbound
  messages — never answers them.
- All of the above default to Mock providers, which touch no real
  external service.

## Data export

- `POST /api/v1/compliance/data-export` (admin-only) searches by
  email/domain/name across companies, contacts, email drafts, replies,
  workflow runs, outreach queue items, dispatches, and do-not-contact
  entries, returning a JSON package.
- Never includes a secret, API key, or token.
- Every export is audited (`data_export_executed`).

## Data deletion / retention

- Data Retention Policies (admin-only) declare a retention window and an
  action (`anonymize`, `delete`, or `archive`) per entity type.
- A dry run never changes data — it only reports what would be affected.
- A real run requires an active policy and an explicit `confirm=true`.
- Active do-not-contact entries are never touched by any run, regardless
  of age — only inactive entries past their retention window are
  eligible.
- Audit logs are append-only by design and are never deleted or
  anonymized by any retention run.
- See `DATA_RETENTION_*` environment variables in `.env.example` for the
  configurable defaults (all safe: disabled, anonymize-first, dry-run
  first).

## Audit logs

- Every security-relevant action (do-not-contact changes, review
  decisions, dispatch attempts, admin control changes, data retention
  runs, data exports, data subject requests, ...) is recorded.
- Audit logs never store secrets, API keys, tokens, full email bodies,
  full reply bodies, or full LLM prompts — see
  `backend/application/audit/audit_log_service.py`'s sanitization.
- Blocked/rejected security actions are recorded durably, independent of
  the request's own transaction (`AuditLogService.record_independent`).

## Backups

- See [`docs/PRODUCTION_CHECKLIST.md`](docs/PRODUCTION_CHECKLIST.md) and
  the Deployment/Monitoring sections of `README.md` for backup setup.
  `DATA_RETENTION_BACKUP_DAYS` documents an intended backup retention
  window but does not itself manage backup files.

## Provider notes

- Mock is the default and only active provider unless explicitly
  overridden. Real providers (Anthropic, Gmail, Outlook) become
  subprocessors for the data they touch once enabled — review their own
  data processing terms before enabling them for real customer data.
- No real "send" scope (`gmail.send`/`Mail.Send`) is ever requested from
  Gmail/Outlook — manual send mode only ever produces a real outcome
  through the Mock provider.

## Legal review required

This compliance pack, the Compliance Documents endpoint
(`GET /api/v1/compliance/documents`), and this file are **prepared for a
legal/compliance review** — they are not a substitute for one. Before any
real, paying customer or real prospect contact:

- Get your own legal review of data processing, retention, and contact
  practices in every applicable jurisdiction.
- Confirm you have a lawful basis to contact each person/company in your
  data.
- Review [`CUSTOMER_READINESS.md`](CUSTOMER_READINESS.md)'s "Before First
  Paid Beta" checklist.
