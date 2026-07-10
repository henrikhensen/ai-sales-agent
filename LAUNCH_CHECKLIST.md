# Launch Checklist

A compact, one-pass go/no-go list for launching this system to a real
(first) customer. It does not replace the detailed checklists below — it
points at them. Work through it in order; every `[ ]` is a deliberate
human confirmation, not something the app can tick for you.

Detailed references: [`docs/PRODUCTION_CHECKLIST.md`](./docs/PRODUCTION_CHECKLIST.md)
(infrastructure), [`CUSTOMER_READINESS.md`](./CUSTOMER_READINESS.md)
(compliance/safety detail), [`BETA_ONBOARDING.md`](./BETA_ONBOARDING.md)
(per-user onboarding), [`DEPLOYMENT.md`](./DEPLOYMENT.md) (runbook).

## 1. Env / Secrets gesetzt

- [ ] `.env` exists on the target host (never committed — `.env.example`
      is the template), with a real, rotated `JWT_SECRET_KEY` and
      `POSTGRES_PASSWORD` (not the example placeholders).
- [ ] `CORS_ALLOWED_ORIGINS` is the exact production frontend origin(s),
      never empty or `*`. With `APP_ENV=production`, the backend
      hard-fails at startup if any of the above are still insecure
      defaults (`backend/shared/production_checks.py`).

## 2. Migrationen ausgeführt

- [ ] `alembic upgrade head` run against the target database (new
      deployment), or `alembic stamp head` (existing DB already matching
      the baseline schema). See `DEPLOYMENT.md` section 5.
- [ ] `alembic check` reports no drift.

## 3. Health Checks grün

- [ ] `GET /health` and `GET /ready` (and their `/api/v1/...` equivalents)
      return 200 against the target deployment, not just locally.
- [ ] `GET /api/v1/system/status` (admin) shows no unexpected production
      warnings.

## 4. Test-User geprüft

- [ ] At least one admin, one reviewer, and one sales account exist on the
      target deployment and can log in (`/login`).
- [ ] RBAC spot-check: a sales-role account cannot reach admin-only pages
      (`/admin/*`, setup checklist) or actions (data retention runs,
      feedback review/archive, dispatch config).

## 5. Safe Defaults aktiv

- [ ] `LLM_PROVIDER=mock`, `EMAIL_INTEGRATION_PROVIDER=mock`,
      `REPLY_TRACKING_PROVIDER=mock`, `OUTREACH_DISPATCH_MODE=draft_only`
      — unless a provider was deliberately switched on (next item).
- [ ] `data_retention_dry_run_default` and
      `data_retention_anonymize_instead_of_delete` are still `true`
      unless a real destructive run was a deliberate, reviewed decision.

## 6. Provider bewusst konfiguriert

- [ ] For every real provider that IS enabled
      (`LLM_ENABLE_REAL_CALLS`, `EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS`,
      `REPLY_TRACKING_ENABLE_REAL_READS`,
      `OUTREACH_DISPATCH_ENABLE_REAL_SEND`), a named person made that
      decision deliberately and understands the cost/quota and
      compliance implications — see `CUSTOMER_READINESS.md` → "Before
      First Paid Beta".

## 7. DNC / Human Review geprüft

- [ ] Do-not-contact list is populated with any known opt-outs before the
      first real send/draft (see `CUSTOMER_READINESS.md`).
- [ ] Do-not-contact blocks and Human Review gates are re-confirmed by the
      automated suite (`tests/test_do_not_contact_service.py`,
      `tests/test_api_do_not_contact_endpoint.py`, and the workflow/
      dispatch tests) — re-run before go-live, don't rely on memory of a
      past run.

## 8. Backup/Restore geprüft

- [ ] `ENABLE_BACKUPS=true` on the target deployment.
- [ ] A restore drill has been rehearsed at least once against a
      disposable database (`DEPLOYMENT.md` section 9) — not just the
      backup script's existence.

## 9. Monitoring/Logs geprüft

- [ ] Uptime monitoring points at `/health` and `/ready`.
- [ ] Logs are shipped somewhere durable (stdout alone disappears on
      container restart) — see `docs/PRODUCTION_CHECKLIST.md` → Logging.
- [ ] Confirm no secret, token, or API key ever appears in logs — spot
      check a few real log lines, don't just trust the code comment.

## 10. Rollback-Pfad bekannt

- [ ] Application rollback: redeploy the previous known-good commit/image
      (this project has no CI/CD pipeline of its own — rollback is a
      manual redeploy on your host).
- [ ] Schema rollback: `alembic downgrade -1` (see `DEPLOYMENT.md`
      section 5) — verify this has actually been tried once against a
      disposable database, not only read about.
- [ ] Data rollback: restore the most recent backup (`DEPLOYMENT.md`
      section 9) if a bad run needs undoing.

## 11. Kein Auto-Send / kein Send-Button-Default

- [x] No send-capable endpoint exists anywhere in the API — enforced by
      `tests/test_deployment_regression.py::test_no_send_endpoint_exists_anywhere`
      and the equivalent per-feature checks (quality, beta-test,
      real-world-test).
- [x] No page renders a default, always-available "send" button. The one
      controlled action that can be construed as risky — "Kontrolliert
      senden" in Outreach — only appears when `OUTREACH_DISPATCH_MODE=
      manual_send` was deliberately configured, and even then requires a
      passed readiness check, a compliance acknowledgement, and an
      explicit checkbox confirmation per action.
- [x] "Approved" / "completed" never means something was sent — verified
      by the standing regression tests across Sales Workflow, Outreach
      Queue, Real-World Test Mode, and Beta Test Sessions.

## Sign-off

- [ ] Named person: ******\_\_\_\_******  Date: ******\_\_\_\_******
- [ ] All 11 sections above reviewed for **this specific deployment
      target** — a prior sign-off on a different environment does not
      carry over.
