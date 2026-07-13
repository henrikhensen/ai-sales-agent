# Project Status

See [`PROJECT_RULES.md`](./PROJECT_RULES.md) for the binding rules
(safety, architecture, process) every phase below follows.

## Current Phase: 44 — Premium AI SaaS Visual Redesign

**Status: implemented. Frontend-only visual redesign (style reference: a
modern venture/deep-tech AI SaaS landing page — silhouettes/typography/
layout inspiration only, no assets, images, logos, or copy copied from
anywhere). No backend logic changed; one small additive backend field
(see below) exists only to satisfy an explicit UI requirement ("Quelle"
on each candidate card). No safety rule loosened, no send capability
added.**

Phase 44 replaces Phase 40's first redesign pass with a more editorial,
"less admin dashboard, more real product" look, and reviews Header,
Sidebar, Start (home), Lead Finder, Settings, Leads (CRM Pipeline), and
Reviews:

- **Design system** (`frontend/tailwind.config.ts`, `frontend/app/
  globals.css`): a new near-black `ink` color scale (separate from
  `slate`, so light work surfaces are untouched) for dark "command-center"
  surfaces; `display-lg`/`display-md` large tight-tracking type sizes;
  `shadow-premium`/`shadow-premium-dark`; a `.hero-dark` utility (dark
  gradient + faint grid backdrop) for the home page hero;
  `.section-eyebrow`/`.section-title` for consistent section headings.
- **New shared components** (`frontend/components/ui/`): `StatusPill`
  (dot + label + detail, light or dark variant — used for safety
  guarantees and live provider status), `SectionHeader` (eyebrow + title +
  description + optional action), `EmptyState` (centered placeholder
  replacing bare "keine Daten" lines), `WorkflowStep` (large numbered step
  card). Existing `Button` (added `size`/`dark` variant), `Card` (rounder,
  `shadow-premium`), `Badge` (bolder weight) got a more premium default
  look, inherited automatically everywhere already in use.
- **Header** (`frontend/components/layout/Header.tsx`): now a dark
  (`bg-ink-950`) bar with a small glowing brand dot — health/role/mock
  badges unchanged in behavior, just restyled (light chips read fine on a
  dark bar). **Sidebar**: active nav item now a solid dark pill; a small
  "AI" logo mark added; structure/routes/RBAC visibility unchanged.
- **Home page** (`frontend/app/page.tsx`, rewritten): new dark
  command-center hero with the exact requested copy — headline "Finde
  Firmen. Analysiere Websites. Bereite Outreach vor.", subline "Ein AI
  Sales Copilot für kontrollierte B2B-Kaltaquise — mit echter
  Firmensuche, Website-Analyse und Human Review.", primary CTA "Lead
  Finder starten", secondary "Letzte Runs ansehen" — with the safety strip
  (Safe/Mock Mode, kein automatischer Versand, Human Review erforderlich,
  Do-not-contact aktiv) embedded directly in the hero via `StatusPill`.
  Workflow steps section renamed to the requested five titles (Zielgruppe
  definieren → Firmen finden → Website analysieren → **Fit bewerten** →
  Draft prüfen — "Lead bewerten" renamed to "Fit bewerten") using the new
  `WorkflowStep` card. Lead Finder still embedded directly, nothing else
  structural changed.
- **Lead Finder** (`frontend/components/lead-finder/LeadFinderApp.tsx`):
  the compliance hint above the form was a bulleted amber wall of text —
  replaced with a single compact one-line strip. Form card enlarged
  (`p-7`/`p-9`), placeholders improved (concrete examples instead of
  generic ones), the Lead Sourcing provider badge moved to the card header
  and reads e.g. "Brave Search aktiv · echte Suche aktiv", submit button
  enlarged (`size="lg"`). Candidate result cards: company name now large/
  bold, a new **Quelle** (source) field shown next to industry/location,
  and a compact "Nächster Schritt"/disqualification-reason line always
  visible (not just inside the expandable details) — score, website
  quality, and status badges unchanged in content. Both empty states
  (no candidates found, no past runs) now use the new `EmptyState`
  component instead of a bare sentence in a plain `Card`.
- **Backend, additive only** (`backend/application/lead_discovery/
  schemas.py`, `lead_discovery_service.py`): `LeadDiscoveryCandidateSummary`
  gained `source_name` (already stored on `LeadCandidate`, e.g. `"brave"`/
  `"mock"` — never fetched again, never guessed) so the Lead Finder result
  card can show where a candidate came from. No migration needed (field
  already existed on the entity/table), no other endpoint/schema touched.
- **Settings** (`frontend/app/settings/page.tsx`): status now reads as
  four clean cards — **Backend**, **Lead Sourcing** (new
  `LeadSourcingStatusCard`, live provider/real-search-enabled/warnings),
  **LLM** (unchanged `LlmProviderStatusCard`), **Safety** (new
  `SafetyStatusCard` — kein automatischer Versand / Human Review
  erforderlich / Do-not-contact aktiv as standing guarantees, plus a live
  "LLM Modus: Mock/Real" pill reusing the existing LLM status fetch). The
  always-visible raw JSON debug block is now inside a collapsed
  `<details>`/`<summary>` ("Debug (rohe API-Antworten anzeigen)") instead
  of always rendered.
- **Leads (CRM Pipeline) / Reviews**: light touch — `SectionHeader` for
  consistent headings, the CRM Pipeline's bulleted compliance notice
  compacted into a one-line strip (same pattern as Lead Finder). Board/
  card layout, pipeline logic, and RBAC unchanged (already card-based, no
  table to redesign).
- **Tests**: `tests/test_frontend_home.py` updated for the new hero copy/
  workflow step title and a new dark-hero-surface check;
  `tests/test_frontend_design_system.py` (new) — the four new shared
  components exist, Settings shows all four status cards with a
  collapsible debug block and the standing safety guarantees, Lead Finder
  cards show `source_name`/"Quelle:", and the compliance hint above the
  form is no longer a bulleted list. `tests/test_frontend_lead_finder.py`
  and `tests/test_frontend_safety.py` pass unchanged (no send-capable UI
  introduced, every previously-required label/field still present).
- **Verified**: full backend suite (1329 tests) green; `cd frontend &&
  npm run typecheck && npm run build`: clean (43 routes built).

## Prior Phase: 43 — Lead Qualification Visibility & Scoring Fix

**Status: implemented. Root cause of "Lead Finder findet echte Firmen, aber
qualifiziert 0 Leads" found and fixed — three compounding bugs in
scoring/status logic, not a data or provider problem. No safety rule
loosened; still no send capability anywhere.**

**Exact causes of 0 qualified leads:**

1. **`min_score` never reached the scorer.** The Lead Finder's own
   "Mindestscore" field (e.g. `0`) was accepted by `LeadDiscoveryService`
   and `CreateLeadDiscoveryRunRequest`, but `LeadQualificationService.
   qualify_lead_candidate()` never forwarded it to `_score_and_save()` —
   every candidate was scored against the app-wide default
   (`LEAD_QUALIFICATION_DEFAULT_MIN_SCORE`, typically 70) regardless of
   what the run actually requested.
2. **`min_score_override or default` treated an explicit `0` as "not
   provided".** Fixing (1) alone wasn't enough — `0 or 70` evaluates to
   `70` in Python (0 is falsy), so even after threading the override
   through, `min_score=0` — the acceptance test's exact input — still
   silently became 70. Caught by a new regression test before it shipped.
3. **The "sparse data" override counted informational-only fields.**
   `qualification_status` was forced to `needs_review` whenever
   `len(missing_data) >= 3`, but `company_size` (never populated anywhere
   for a Lead-Sourcing-originated candidate — there is no data source for
   it) and `public_contact_email` (rarely present for a fresh company)
   never affect the score at all, yet both counted toward this threshold.
   Two permanently-missing, score-irrelevant fields plus one real gap was
   enough to force every real-world candidate into `needs_review`
   regardless of an otherwise good score. Replaced with a counter of only
   the four fields that actually influence the score (ICP fit, industry,
   location, website text).

None of this was a Brave/provider/website-research bug — real candidates
were always being found and scored; the status logic just never let a
realistic score become `"qualified"`.

**What changed:**

- **`backend/application/lead_qualification/qualification_scoring_service.py`**:
  `QualificationInput` gained `website_quality_level`/`website_quality_reasons`/
  `offer_targets_outdated_websites`; `_determine_status` now takes a
  `score_confidence_gaps` count (see cause 3) instead of `len(missing_data)`;
  new website-quality-vs-offer-fit block — for an offer that's itself about
  fixing an outdated website, a `poor`/`unknown` website is now a **positive**
  signal (+15) and `medium` a smaller one (+8), while `good` is a small
  negative (-5) — the opposite of the old "more data is always better"
  assumption, which was actively wrong for this use case.
- **`backend/application/lead_qualification/lead_qualification_service.py`**:
  `_score_and_save`'s `min_score` resolution fixed (cause 2);
  `QualifyLeadCandidateRequest`/`QualifyCRMLeadRequest` gained `min_score`;
  `_build_input_for_candidate`/`_build_input_for_lead` now accept
  `offer_profile_id`, detect a website-relaunch-style offer via keyword
  match on its own name/value-proposition/pain-points/benefits text (never
  guessed from anything else), and pass the candidate's already-computed
  `website_quality_level`/`reasons` through; a missing offer profile now
  also produces an explicit "no offer profile specified" warning,
  symmetric with the existing missing-ICP warning.
- **`backend/application/lead_sourcing/lead_sourcing_service.py`**
  `assess_website_quality`: rewritten with concrete, auditable signals —
  outdated copyright year, literal stale-tech markers (frames, "best
  viewed with", ...), CTA-phrase presence, services/"Leistungen"
  presence, contact-info presence, and (new, see below) a real viewport
  meta tag check — every reason is still text already fetched, never
  fabricated.
- **`backend/infrastructure/web/sanitizer.py` /
  `backend/application/research/*`**: `has_viewport_meta` — a real,
  non-guessed proxy for "declares itself mobile-aware" — threaded through
  `ExtractedPage` → `WebsiteResearchResponse`, used by the above.
- **`backend/application/lead_discovery/lead_discovery_service.py`**:
  `run_pipeline` now forwards `run.min_score` to qualification (cause 1);
  a `needs_review` outcome is counted separately (`needs_review_leads`,
  new column — migration `b7e51c9a4d3f`) instead of being folded into
  `rejected_leads`; when `qualified_leads == 0`, `run.warnings` gets a
  synthesized, per-reason breakdown ("0 Leads erreichen den Mindestscore
  (0). Ablehnungsgründe: ...") plus a note pointing at any `needs_review`
  candidates ready for manual review.
- **`backend/application/lead_discovery/schemas.py`**:
  `LeadDiscoveryCandidateSummary` gained `missing_data` and
  `disqualification_reason` — previously computed but never surfaced to
  the Lead Finder UI at all.
- **`backend/application/outreach/outreach_queue_service.py`**
  `build_queue`: every skip branch (below min_score, disqualified,
  duplicate, wrong level, excluded status) now appends an explicit
  warning — previously several skipped silently, so a manual "add to
  queue" override could do nothing with no visible reason.
- **`backend/application/quality/quality_scoring_service.py`** /
  `backend/api/v1/dependencies.py`: unrelated pre-existing bug this fix
  exposed — `auto_score`'s `except Exception` block logged and returned
  `None` but never rolled back the (now request-scoped, optionally
  injected) session, so a transient failure while scoring one email draft
  left the session unusable for every later query in the same request.
  Never triggered before because this exact test path never created a
  real email draft (see cause 1); now rolls back on failure, restoring
  the method's own documented "never breaks the action it's observing"
  guarantee. `session: AsyncSession | None = None` — optional, so no
  existing fake-based test/call site changed.
- **Frontend** (`frontend/components/lead-finder/LeadFinderApp.tsx`):
  German status labels (`needs_review` → "Zu prüfen", etc.); per-candidate
  `missing_data` and `disqualification_reason` shown in the expanded view;
  run summary line now shows "N zu prüfen" as its own count; the queue
  button reads "Als Lead übernehmen" for qualified/priority and "Manuell
  prüfen (Zur Review Queue hinzufügen)" otherwise — a candidate is never
  only a bare 0/0 result.

**Tests added** (`tests/test_lead_qualification_service.py`,
`tests/test_lead_discovery_service.py`): `min_score=0` produces
`"qualified"` where the same score at the default (70) produces
`"needs_review"`; the override reaches the scorer end-to-end (not just
the pure scoring function); missing `company_size`/email alone no longer
forces `needs_review`; a website-relaunch offer scores a poor website
higher than a good one and says why; a missing offer profile produces a
warning; existing pipeline/queue tests updated for the new
`needs_review_leads` counter.

**Verified**: full backend suite (1322 tests) green; frontend
typecheck/build green; live smoke test against the local docker-compose
stack (migration `b7e51c9a4d3f` applied, both containers rebuilt) — a
freshly imported, realistic "Handwerksbetrieb mit veralteter Website"
candidate with almost no data (no industry/location/website text/ICP)
scored 60 and landed as `needs_review` ("zu prüfen") with the
website-relaunch positive signal correctly applied and every gap listed
in `missing_data` — not silently dropped. **Not verified**: the "no
`*.example` mock domains" acceptance criterion, since this local
environment has no real `BRAVE_SEARCH_API_KEY` configured — the mock
provider's small, already-duplicate-heavy demo pool was used instead to
prove the logic fix; a real Brave-backed run is needed to confirm that
specific criterion.

## Prior Phase: 42 — Railway Deployment Readiness

**Update (same phase): "Backend: offline" kept showing in the deployed
frontend even after `NEXT_PUBLIC_API_BASE_URL`, the backend's public
networking port, and `CORS_ALLOWED_ORIGINS` were all already correct —
root cause was a frontend health-check logic bug, not configuration.**
`GET /api/v1/health` correctly returns `"degraded"` (not `"ok"`) whenever
any component is down — and Redis is deliberately optional on Railway
(rate limiting already falls back to in-memory), so `"degraded"` is the
permanent, expected steady state there. `frontend/components/layout/
Header.tsx`'s health badge treated anything other than an exact `"ok"`
match as fully "offline", conflating "reachable but one optional
dependency is down" with "unreachable". Fixed by adding a third
`"degraded"` state (amber "online (eingeschränkt)"), reserving "offline"
(red) for an actual failed fetch. The "Firmensuche: Mock" badge
(`LeadFinderApp.tsx`) was already correct — it reflects the real,
deliberately-mock `LEAD_SOURCING_PROVIDER` setting, not a bug. Audited
the full API client (`frontend/lib/api.ts`) for the checklist this fix
was requested against: only `NEXT_PUBLIC_API_BASE_URL` is read anywhere
in the frontend (no `BACKEND_PUBLIC_URL`/`NEXT_PUBLIC_BACKEND_URL`
double-reads exist), every request path already appends its own
`/api/v1/...` exactly once, and the only `localhost:8000` references are
the local-dev fallback/Dockerfile ARG default/`.env.example` — all
correctly inert once the real Railway value is set at build time, so
none needed removal. Added a small always-visible "Debug" block to
`/settings`'s existing "Backend-Verbindung" card (`BackendDiagnostics`,
new, in `frontend/app/settings/page.tsx`): the resolved health-endpoint
URL and the raw `GET /api/v1/health` / `GET /api/v1/lead-sourcing/status`
JSON responses — no secrets in either payload, so nothing new is exposed
that admin-only `/settings` didn't already show.

**Prior update (same phase): first real Railway deploy crash-looped — root
cause was environment configuration, not application code.** The
`backend` service's Railway Variables had the local `docker-compose`
values (`POSTGRES_HOST=postgres`, `REDIS_HOST=redis`) pasted in directly
instead of `DATABASE_URL`/`REDIS_URL` — those hostnames only resolve
inside the local compose network, so `init_database()` (awaited in
`backend/main.py`'s `lifespan`, before the app can serve any request)
failed DNS resolution and the container exited non-zero on every start.
Fix is env-configuration only (see `DEPLOYMENT_RAILWAY.md` section 10,
new): set `DATABASE_URL=${{Postgres.DATABASE_URL}}` and drop the discrete
`POSTGRES_*`/`REDIS_*` vars. Two new `railway.toml` files (repo root for
`backend`, `frontend/railway.toml` for `frontend`) pin each service's
Dockerfile path/start command/healthcheck explicitly, removing the
build-tool auto-detection ambiguity that a single misconfigured service
(no distinct Root Directory for `frontend`) had been running into. No
application code changed; both Dockerfiles already read `$PORT`/bind
`0.0.0.0` correctly (Phase 42's original port fix, unchanged and
confirmed still correct). Full backend suite (1317 tests) and frontend
typecheck/build re-verified green after this fix.

**Status: implemented. The project can now be deployed publicly to Railway
with a minimal-click path. No backend/frontend application logic changed;
no safety default loosened — Mock/Safe Mode, draft-only dispatch, and
disabled real-send stay the defaults.**

Phase 42 is deployment scaffolding only — it prepares this repo's existing
two Dockerfiles for Railway (or any PaaS that injects a dynamic `$PORT`)
and documents the exact click path, without adding any new service,
endpoint, or automation:

- **`Dockerfile` (backend)**: `CMD`/`HEALTHCHECK` previously hardcoded port
  8000 as a Docker exec-form array, which cannot expand shell variables —
  so a host injecting its own `$PORT` (Railway, Render, etc.) was silently
  ignored. Now shell-form (`CMD uvicorn ... --port ${PORT:-8000}`) with a
  `HEALTHCHECK` that reads `$PORT` via Python, defaulting to 8000 when
  unset (unchanged behavior for `docker-compose.yml`, which explicitly
  overrides `command:` anyway).
- **`frontend/Dockerfile`**: `server.js` (Next.js standalone output)
  already reads `process.env.PORT` itself; only its `HEALTHCHECK` was
  hardcoded to 3000 — fixed to read `process.env.PORT` the same way.
- **`.env.production.example`** (new, repo root): a focused production
  environment template — `APP_ENV=production`, `DATABASE_URL`/`REDIS_URL`
  override guidance, required `JWT_SECRET_KEY`/`CORS_ALLOWED_ORIGINS`, and
  every provider left at its safe default (`LLM_PROVIDER=mock`,
  `EMAIL_INTEGRATION_PROVIDER=mock` + `EMAIL_INTEGRATION_ENABLE_REAL_DRAFTS
  =false`, `REPLY_TRACKING_PROVIDER=mock`, `LEAD_SOURCING_PROVIDER=mock`,
  `OUTREACH_DISPATCH_MODE=draft_only` + `OUTREACH_DISPATCH_ENABLE_REAL_SEND
  =false`). Complements, does not duplicate, the full documented list in
  `.env.example`.
- **`DEPLOYMENT_RAILWAY.md`** (new, repo root): exact Railway click path
  (3 services — `backend`, `frontend`, managed Postgres; Redis optional
  since rate limiting already falls back to an in-memory counter), every
  environment variable each service needs, confirmation that no Start
  Command override is needed (the Dockerfiles' own `CMD` already reads
  `$PORT`), the migration command (`alembic stamp head` after first
  deploy, since `init_database()`'s existing `CREATE TABLE IF NOT EXISTS`
  already gives a fresh Railway Postgres the full schema on first
  startup — matching `DEPLOYMENT.md` section 5's "existing deployment"
  path exactly), optional Railway CLI steps (no secrets ever echoed),
  health/login URLs to check, custom-domain/DNS steps, and an end-to-end
  acceptance test. Cross-referenced from `DEPLOYMENT.md`,
  `docs/DEPLOYMENT_GUIDE.md`'s "Option: Railway" section, and a new short
  README pointer.
- **Local environment cleanup**: the local (gitignored, never committed)
  `.env` had been left in real Brave Search mode
  (`LEAD_SOURCING_PROVIDER=brave`, `LEAD_SOURCING_ENABLE_REAL_SEARCH=true`)
  with no API key from Phase 41 testing, plus a stray control byte —
  together these made the local backend test suite issue real (failing)
  HTTP calls instead of using the mock provider. Reverted to
  `LEAD_SOURCING_PROVIDER=mock` / `LEAD_SOURCING_ENABLE_REAL_SEARCH=false`
  per `DEPLOYMENT.md` section 10 ("Back to Mock") and rewrote the file
  cleanly; no committed file was affected (`.env` stays gitignored).
- **Verification**: `docker compose down` → `docker compose up -d
  --build` (both images build, all four containers report healthy);
  full backend suite (`python -m pytest -q`, run on the host per
  `DEPLOYMENT.md`'s own convention — the backend image intentionally
  contains only `backend/` + `alembic.ini`, not `frontend/`/`.env`/etc.,
  so the source-level frontend/deployment regression tests only make
  sense on the host): **1317 passed**; frontend `npm run typecheck` and
  `npm run build`: clean; `GET /health`, `/ready`, `/api/v1/ready`,
  `/docs` (backend) and `/`, `/login` (frontend): all respond correctly.

## Prior Phase: 41 — Brave Search Real Lead Sourcing Provider

**Status: implemented. Lead Finder can now use real Brave Search web
results instead of the mock provider, opt-in only. Safe/Mock stays the
default; no sending capability was added.**

Phase 41 adds a fourth Lead Sourcing provider — `BraveLeadSourcingProvider`
— alongside the existing mock/manual/search_api providers, following the
exact same two-flag opt-in pattern as every other real provider in this
project:

- **`backend/infrastructure/lead_sourcing/brave_provider.py`** (new):
  calls the real Brave Search Web API
  (`https://api.search.brave.com/res/v1/web/search`), authenticated via
  the `X-Subscription-Token` header — never a query parameter, never
  logged. Builds its query from `target_industry` + `target_location` +
  `target_keywords`, appends `excluded_keywords` as Brave's own `-term`
  syntax, and **re-filters the response itself** afterwards (title +
  description substring match) rather than trusting the remote API
  alone to honor the exclusion. Maps each result to the existing
  `RawLeadCandidate` shape (title → `company_name`, url →
  `company_website_url`/`source_url`, description → `description`,
  `source_name="brave"`) and attaches a truncated (≤500 char) raw
  snapshot for audit purposes. HTTP errors, timeouts, and non-2xx
  responses (401/403/429/5xx) all raise
  `LeadSourcingProviderNotConfiguredError` with a clear, secret-free
  message — mirroring the Gmail/Outlook provider's existing
  try/except/status-code pattern, never a silent empty result.
- **Provider selection** (`backend/infrastructure/lead_sourcing/
  factory.py`): `LEAD_SOURCING_PROVIDER=brave` only ever runs when
  `LEAD_SOURCING_ENABLE_REAL_SEARCH=true` is *also* set — exactly like
  `search_api` already worked. Critically, a missing
  `BRAVE_SEARCH_API_KEY` does **not** make the factory fall back to
  Mock — it still returns a `BraveLeadSourcingProvider`, which then
  blocks the actual `search_companies()` call with a clear error. Mock
  is only ever selected when `LEAD_SOURCING_PROVIDER=mock` or
  `LEAD_SOURCING_ENABLE_REAL_SEARCH=false`.
- **Config** (`backend/shared/config.py`): new `brave_search_api_key`
  (alias `BRAVE_SEARCH_API_KEY`, default `None`) — never logged, never
  returned by any API response, never sent to the frontend.
- **`RawLeadCandidate.raw_snapshot`** (new, optional field on the
  existing dataclass in `backend/infrastructure/lead_sourcing/base.py`,
  threaded through `normalize_candidate()`): a provider-agnostic hook for
  attaching a truncated raw-source audit trail, appended to the
  candidate's `notes` by `LeadSourcingService._process_candidate` when
  present. Available to any future provider, not just Brave.
- **Frontend**: `/lead-sourcing`'s candidate detail view now renders
  Website/Source URL as real clickable links instead of plain text. The
  Lead Finder (`LeadFinderApp.tsx`) now fetches and displays the live
  Lead Sourcing provider status (`GET /api/v1/lead-sourcing/status`) as
  a badge — "Mock (Safe Mode)" or "Brave Search (echte Suche aktiv)" —
  so Real Mode is visibly confirmed rather than assumed; the badge only
  ever renders fields already present in the existing status response
  (provider, real_search_enabled, warnings) and never a key/secret.
- **Tests**: `tests/test_lead_sourcing_brave_provider.py` (new, 17
  tests) — config loading, provider selection (mock fallback when real
  search disabled, Brave used when enabled+configured, missing key
  blocks rather than falling back), the adapter mapping a mocked Brave
  API response (success, excluded-keyword filtering, empty query short-
  circuit, 401/403/429/5xx and timeout/connection-error handling, via
  the same `httpx.AsyncClient` monkeypatch convention already used for
  Gmail/Outlook), and the standing guarantee that Brave real-mode
  candidates never contain the mock provider's `*.example` data.
  `tests/test_api_lead_sourcing_endpoint.py` (+1) confirms the status
  endpoint reflects `provider="brave"` without ever exposing the key in
  the response body. `tests/test_frontend_lead_finder.py` (+2) checks
  the new provider badge renders and never hardcodes a secret-shaped
  value. All existing Lead Sourcing/Lead Discovery tests pass unchanged.

## Prior Phase: 40 — Modern Copilot Redesign

**Status: implemented. The frontend no longer reads as an admin
dashboard — the home page is a landing-style page with the Lead Finder
embedded as the primary, prominent entry point. No sending functionality
was added; no backend logic changed beyond what the redesign needed.**

Phase 40 is a frontend-only visual/structural redesign (style reference:
a modern agency/SaaS landing page, used only for layout/typography
inspiration — no assets or copy were copied) with no backend changes:

- **New home page** (`frontend/app/page.tsx`, rewritten): a hero section
  (headline, subline stating no automatic sending, primary CTA "Lead
  Finder starten" that scrolls to the embedded Lead Finder, secondary
  CTA "Letzte Analysen ansehen" that scrolls to its "Letzte Runs" cards),
  a prominent **Safety Strip** (Safe/Mock Mode, kein automatischer
  Versand, Human Review erforderlich, Do-not-contact aktiv — the first
  driven by live `OnboardingReadinessChecks` data, the rest standing
  product guarantees), five numbered **workflow step cards** (Zielgruppe
  definieren → Firmen finden → Website analysieren → Lead bewerten →
  Draft prüfen), the **Lead Finder embedded directly** (not just
  linked), and a single de-emphasized "Weitere Werkzeuge" links row. The
  old dense multi-widget "Überblick" grid (Letzte Workflows / Leads mit
  nächstem Schritt / Offene Reviews / Letzte Warnings as four separate
  tables) and the 6-step interactive journey tracker from Phase 38 are
  gone — superseded by the Lead Finder's own "Letzte Runs" cards, which
  already show status, found/qualified counts, warnings, and next step
  per run.
- **`LeadFinderApp` extracted** (`frontend/components/lead-finder/
  LeadFinderApp.tsx`, new): the full Lead Finder (form, results,
  "Letzte Runs") moved out of `app/lead-finder/page.tsx` into a shared,
  reusable component with an `embedded` prop (suppresses the page-level
  H1 when embedded on the home page). `/lead-finder` now renders the
  same component standalone — one implementation, two entry points, no
  duplicated state/logic. The submit button now reads "Firmen finden &
  Websites analysieren" and past runs render as cards (name, status,
  found/qualified counts, warning count, next-step hint) instead of a
  plain list row.
- **Navigation reduced to five destinations**
  (`frontend/components/layout/Sidebar.tsx`, rewritten): Start, Lead
  Finder, Reviews, Leads (→ CRM Pipeline), Einstellungen — down from the
  previous five grouped sections. Every other route (Setup-Guide, ICP,
  Offer, Lead Sourcing, Lead Qualification, single-company Sales
  Workflow, Outreach Queue/Dispatch, Replies, Compliance, Audit Logs,
  System Status, Users, Admin Controls, Quality/Beta/Real-World Test,
  Agents, Website Research) still exists and is still reachable under a
  single collapsed "Erweitert" disclosure — nothing was removed, only
  regrouped.
- **UI polish**: `Card` (rounded-2xl, softer shadow) and `Button`
  (rounded-xl, semibold, subtle shadow on the primary variant) got a
  slightly more premium default look, applied automatically everywhere
  they're already used — no page had to change to pick it up. Two new
  global utility classes (`.eyebrow`, `.hero-surface`) support the new
  landing-style sections.
- **Tests**: `tests/test_frontend_safety.py` (new, 1 test) — the
  standing "no Senden/Versenden label anywhere" regression, extracted
  so it survives independent of any one page's content.
  `tests/test_frontend_home.py` (new, replaces the old Command-Center
  test file, 12 tests) — hero, safety strip, workflow steps, embedded
  Lead Finder, no dense tables, five-item Sidebar, "Erweitert" still
  reaches every admin route. `tests/test_frontend_lead_finder.py`
  (updated) — now reads the shared `LeadFinderApp.tsx` component instead
  of the thin page wrapper. All backend tests unaffected (no backend
  code changed in this phase).

## Prior Phase: 39 — Guided Lead Discovery Agent ("Lead Finder")

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

- Phase 44: premium AI SaaS visual redesign
- Phase 43: lead qualification visibility and scoring fix
- Phase 42: Railway deployment readiness
- Phase 41: Brave Search real lead sourcing provider
- Phase 40: modern Copilot redesign
- Phase 39: guided lead discovery agent ("Lead Finder")
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

## Standing Guarantees (apply to every phase, including 42)

- Mock provider is the default everywhere; real providers require
  explicit, separate configuration.
- No automatic email sending, no batch send, no reply-send endpoint, no
  automatic external draft creation.
- Do-not-contact and Human Review are never bypassed by any feature.
- "Approved" / "completed" never means something was sent.
- No secrets, API keys, or tokens are ever logged, committed, or shown in
  the frontend.
