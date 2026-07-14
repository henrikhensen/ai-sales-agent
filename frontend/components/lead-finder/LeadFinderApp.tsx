"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Reveal } from "@/components/ui/Reveal";
import { Select } from "@/components/ui/Select";
import { Skeleton, SkeletonRunCard } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/ToastProvider";
import {
  ApiError,
  addLeadDiscoveryCandidateToQueue,
  createLeadDiscoveryDrafts,
  createLeadDiscoveryRun,
  getICPProfiles,
  getLeadDiscoveryRun,
  getLeadDiscoveryRuns,
  getLeadSourcingStatus,
  getOfferProfiles,
  runLeadDiscoveryPipeline,
} from "@/lib/api";
import type {
  ICPProfile,
  LeadDiscoveryCandidateSummary,
  LeadDiscoveryRun,
  LeadDiscoveryRunDetail,
  LeadSourcingProviderStatus,
  OfferProfile,
} from "@/lib/types";

const PROVIDER_LABEL: Record<string, string> = {
  mock: "Mock",
  brave: "Brave Search",
  search_api: "Such-API",
  manual: "Manuell",
};

type BadgeTone = "positive" | "info" | "warning" | "negative" | "neutral";

const WEBSITE_QUALITY_LABEL: Record<string, string> = {
  good: "Gut",
  medium: "Mittel",
  poor: "Schlecht",
  unknown: "Unbekannt",
};
const WEBSITE_QUALITY_TONE: Record<string, BadgeTone> = {
  good: "positive",
  medium: "warning",
  poor: "negative",
  unknown: "neutral",
};

const ICP_FIT_LABEL: Record<string, string> = {
  excellent: "Exzellent",
  good: "Gut",
  medium: "Mittel",
  weak: "Schwach",
  not_fit: "Kein Fit",
};
const ICP_FIT_TONE: Record<string, BadgeTone> = {
  excellent: "positive",
  good: "positive",
  medium: "warning",
  weak: "negative",
  not_fit: "negative",
};

const QUALIFICATION_STATUS_TONE: Record<string, BadgeTone> = {
  qualified: "positive",
  priority: "positive",
  needs_review: "warning",
  disqualified: "negative",
  blocked: "negative",
  duplicate: "neutral",
};

const QUALIFICATION_STATUS_LABEL: Record<string, string> = {
  qualified: "Qualifiziert",
  priority: "Priorität",
  needs_review: "Zu prüfen",
  disqualified: "Nicht geeignet",
  blocked: "Blockiert (Do-not-contact)",
  duplicate: "Duplikat",
};

const DRAFT_STATUS_LABEL: Record<string, string> = {
  none: "Kein Draft",
  prepared: "In Vorbereitung",
  review_pending: "Bereit zur Prüfung",
};
const DRAFT_STATUS_TONE: Record<string, BadgeTone> = {
  none: "neutral",
  prepared: "info",
  review_pending: "positive",
};

const RUN_STATUS_TONE: Record<string, BadgeTone> = {
  pending: "neutral",
  running: "warning",
  completed: "positive",
  failed: "negative",
};

const RUN_STATUS_LABEL: Record<string, string> = {
  pending: "Ausstehend",
  running: "Läuft",
  completed: "Abgeschlossen",
  failed: "Fehlgeschlagen",
};

// Indicative only — the backend runs these four phases synchronously and
// in this exact order (see LeadDiscoveryService.run_pipeline), but does
// not stream per-phase progress, so this is a client-side "what's likely
// happening now" waiting indicator, not a live progress bar tied to real
// server events.
const SEARCH_STEPS = ["Firmen suchen", "Websites prüfen", "Fit bewerten", "Review vorbereiten"];
const SEARCH_STEP_INTERVAL_MS = 900;

type CandidateFilter = "all" | "needs_review" | "qualified" | "disqualified";

const CANDIDATE_FILTER_LABEL: Record<CandidateFilter, string> = {
  all: "Alle",
  needs_review: "Zu prüfen",
  qualified: "Qualifiziert",
  disqualified: "Abgelehnt",
};

function matchesCandidateFilter(
  candidate: LeadDiscoveryCandidateSummary,
  filter: CandidateFilter
): boolean {
  if (filter === "all") return true;
  if (filter === "qualified") {
    return candidate.qualification_status === "qualified" || candidate.qualification_status === "priority";
  }
  if (filter === "disqualified") {
    return candidate.qualification_status === "disqualified" || candidate.qualification_status === "blocked";
  }
  return candidate.qualification_status === filter;
}

interface FormState {
  target_customer: string;
  region: string;
  offer_profile_id: string;
  icp_profile_id: string;
  requested_count: string;
  min_score: string;
}

const INITIAL_FORM: FormState = {
  target_customer: "",
  region: "",
  offer_profile_id: "",
  icp_profile_id: "",
  requested_count: "10",
  min_score: "50",
};

function CandidateRow({
  candidate,
  expanded,
  onToggle,
  onAddToQueue,
  busy,
}: {
  candidate: LeadDiscoveryCandidateSummary;
  expanded: boolean;
  onToggle: () => void;
  onAddToQueue: () => void;
  busy: boolean;
}) {
  const blocked = candidate.do_not_contact_status === "blocked";
  const nextStep = blocked
    ? null
    : candidate.disqualification_reason
      ? candidate.disqualification_reason
      : candidate.email_draft_id
        ? "Nächster Schritt: Draft prüfen"
        : candidate.in_outreach_queue
          ? "Nächster Schritt: Draft erstellen"
          : candidate.qualification_status === "qualified" ||
              candidate.qualification_status === "priority"
            ? "Nächster Schritt: Als Lead übernehmen"
            : candidate.qualification_status
              ? "Nächster Schritt: Manuell prüfen"
              : null;

  return (
    <Card interactive className={blocked ? "border-l-4 border-l-rose-500" : undefined}>
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="min-w-0">
          <p className="truncate text-2xl font-black tracking-tight text-muted">
            {candidate.company_name ?? "Unbekannte Firma"}
          </p>
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted/55">
            {candidate.company_website_url ? (
              <a
                href={candidate.company_website_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 border border-muted px-2.5 py-1 text-xs font-bold text-muted transition-colors hover:bg-muted hover:text-canvas"
              >
                Website öffnen ↗
              </a>
            ) : null}
            {candidate.source_name ? (
              <span>Quelle: {PROVIDER_LABEL[candidate.source_name] ?? candidate.source_name}</span>
            ) : null}
            <span>{[candidate.industry, candidate.location].filter(Boolean).join(" · ") || "—"}</span>
          </div>
        </div>
        <div className="flex flex-none flex-wrap items-center gap-2">
          <Badge tone={WEBSITE_QUALITY_TONE[candidate.website_quality_level ?? ""] ?? "neutral"}>
            Website: {WEBSITE_QUALITY_LABEL[candidate.website_quality_level ?? ""] ?? "—"}
          </Badge>
          {candidate.icp_fit_level ? (
            <Badge tone={ICP_FIT_TONE[candidate.icp_fit_level] ?? "neutral"}>
              ICP-Fit: {ICP_FIT_LABEL[candidate.icp_fit_level] ?? candidate.icp_fit_level}
              {candidate.icp_fit_score !== null ? ` (${candidate.icp_fit_score})` : ""}
            </Badge>
          ) : null}
          {candidate.qualification_score !== null ? (
            <span className="inline-block animate-scale-in">
              <Badge tone={QUALIFICATION_STATUS_TONE[candidate.qualification_status ?? ""] ?? "neutral"}>
                Score {candidate.qualification_score} ·{" "}
                {QUALIFICATION_STATUS_LABEL[candidate.qualification_status ?? ""] ??
                  candidate.qualification_status}
              </Badge>
            </span>
          ) : (
            <Badge tone="neutral">Noch nicht qualifiziert</Badge>
          )}
          {blocked ? <Badge tone="negative">Do-not-contact</Badge> : null}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs">
        <Badge tone={DRAFT_STATUS_TONE[candidate.draft_status]}>
          Draft: {DRAFT_STATUS_LABEL[candidate.draft_status]}
        </Badge>
        <Badge tone={candidate.in_outreach_queue ? "positive" : "neutral"}>
          {candidate.in_outreach_queue ? "In Review Queue" : "Nicht in Queue"}
        </Badge>
      </div>

      {nextStep ? (
        <div className="mt-5 border-t border-muted/12 pt-4">
          <p className="mono-label">Nächster Schritt</p>
          <p
            className={`mt-1 text-sm font-medium ${
              candidate.disqualification_reason ? "text-rose-300" : "text-muted/80"
            }`}
          >
            {nextStep}
          </p>
        </div>
      ) : null}

      <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-muted/12 pt-4">
        <Button variant="secondary" onClick={onToggle}>
          {expanded ? "Details ausblenden" : "Details ansehen"}
        </Button>
        {candidate.email_draft_id ? (
          <Link
            href="/crm"
            className="inline-flex items-center justify-center gap-2 border border-muted px-4 py-2 text-xs font-bold text-muted transition-colors hover:bg-muted hover:text-canvas"
          >
            Draft prüfen →
          </Link>
        ) : null}
        {!candidate.in_outreach_queue && !blocked ? (
          <Button variant="ghost" loading={busy} onClick={onAddToQueue}>
            {candidate.qualification_status === "qualified" ||
            candidate.qualification_status === "priority"
              ? "Als Lead übernehmen"
              : "Manuell prüfen (Zur Review Queue hinzufügen)"}
          </Button>
        ) : null}
      </div>

      <div
        className={`grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none ${
          expanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
        }`}
      >
        <div className="overflow-hidden">
        <div className="mt-5 space-y-4 border-t border-muted/12 pt-4 text-sm">
          {candidate.fit_summary ? <p className="text-muted/80">{candidate.fit_summary}</p> : null}
          {candidate.disqualification_reason ? (
            <p className="border-l-4 border-l-rose-500 py-1 pl-3 text-xs text-rose-300">
              Ablehnungsgrund: {candidate.disqualification_reason}
            </p>
          ) : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mono-label">Warum geeignet</p>
              {candidate.positive_signals.length === 0 ? (
                <p className="mt-1 text-xs text-muted/55">Keine Angaben.</p>
              ) : (
                <ul className="mt-1 list-inside list-disc text-xs text-muted/80">
                  {candidate.positive_signals.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <p className="mono-label">Warum ungeeignet</p>
              {candidate.negative_signals.length === 0 ? (
                <p className="mt-1 text-xs text-muted/55">Keine Angaben.</p>
              ) : (
                <ul className="mt-1 list-inside list-disc text-xs text-rose-300">
                  {candidate.negative_signals.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          {candidate.missing_data.length > 0 ? (
            <div>
              <p className="mono-label">Fehlende Daten für diese Bewertung</p>
              <ul className="mt-1 list-inside list-disc text-xs text-muted/80">
                {candidate.missing_data.map((m) => (
                  <li key={m}>{m}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <div>
            <p className="mono-label">Gefundene Probleme auf der Website</p>
            {candidate.website_quality_reasons.length === 0 ? (
              <p className="mt-1 text-xs text-muted/55">Keine Angaben.</p>
            ) : (
              <ul className="mt-1 list-inside list-disc text-xs text-muted/80">
                {candidate.website_quality_reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            )}
          </div>
          {candidate.warnings.length > 0 ? (
            <div className="border-l-4 border-l-amber-500 py-1 pl-3">
              <p className="mono-label">Warnings</p>
              <ul className="mt-1 list-inside list-disc text-xs text-muted/80">
                {candidate.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
        </div>
      </div>
    </Card>
  );
}

interface LeadFinderAppProps {
  /** Renders a shorter intro (no page-level H1) when embedded on a page
   * that already has its own hero, e.g. the home page. */
  embedded?: boolean;
}

export function LeadFinderApp({ embedded = false }: LeadFinderAppProps) {
  const { showToast } = useToast();
  const [offers, setOffers] = useState<OfferProfile[]>([]);
  const [icps, setIcps] = useState<ICPProfile[]>([]);
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [searchStep, setSearchStep] = useState(0);
  const searchStepTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<LeadDiscoveryRunDetail | null>(null);
  const [pastRuns, setPastRuns] = useState<LeadDiscoveryRun[]>([]);
  const [expandedCandidateId, setExpandedCandidateId] = useState<string | null>(null);
  const [busyCandidateId, setBusyCandidateId] = useState<string | null>(null);
  const [creatingDrafts, setCreatingDrafts] = useState(false);
  const [providerStatus, setProviderStatus] = useState<LeadSourcingProviderStatus | null>(
    null
  );
  const [candidateFilter, setCandidateFilter] = useState<CandidateFilter>("all");
  const [sortByScore, setSortByScore] = useState(false);
  const [candidateSearch, setCandidateSearch] = useState("");
  const resultRef = useRef<HTMLDivElement>(null);

  const visibleCandidates = useMemo(() => {
    if (!run) return [];
    const query = candidateSearch.trim().toLowerCase();
    let list = run.candidates.filter((candidate) => matchesCandidateFilter(candidate, candidateFilter));
    if (query) {
      list = list.filter((candidate) =>
        [candidate.company_name, candidate.industry, candidate.location]
          .filter(Boolean)
          .some((field) => field!.toLowerCase().includes(query))
      );
    }
    if (sortByScore) {
      list = [...list].sort((a, b) => (b.qualification_score ?? -1) - (a.qualification_score ?? -1));
    }
    return list;
  }, [run, candidateFilter, candidateSearch, sortByScore]);

  const loadInitialData = useCallback(async () => {
    setLoadingProfiles(true);
    try {
      const [offerResponse, icpResponse, runsResponse] = await Promise.all([
        getOfferProfiles(true),
        getICPProfiles(true),
        getLeadDiscoveryRuns({ limit: 10 }),
      ]);
      setOffers(offerResponse.items);
      setIcps(icpResponse.items);
      setPastRuns(runsResponse.items);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Profile konnten nicht geladen werden."
      );
    } finally {
      setLoadingProfiles(false);
    }
    try {
      const status = await getLeadSourcingStatus();
      setProviderStatus(status);
    } catch {
      // Informational only — the form still works without it.
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Belt-and-suspenders cleanup — handleSubmit's own `finally` already
  // clears this, but a component unmount mid-search (navigating away)
  // must not leave a dangling interval.
  useEffect(() => {
    return () => {
      if (searchStepTimer.current) clearInterval(searchStepTimer.current);
    };
  }, []);

  async function refreshPastRuns() {
    try {
      const runsResponse = await getLeadDiscoveryRuns({ limit: 10 });
      setPastRuns(runsResponse.items);
    } catch {
      // The past-runs list is informational only — a failure here should
      // never block the main result view.
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!form.offer_profile_id) {
      setError("Bitte ein Angebot auswählen.");
      return;
    }
    setSubmitting(true);
    setSearchStep(0);
    setError(null);
    setRun(null);
    setCandidateFilter("all");
    setCandidateSearch("");
    searchStepTimer.current = setInterval(() => {
      setSearchStep((step) => Math.min(step + 1, SEARCH_STEPS.length - 1));
    }, SEARCH_STEP_INTERVAL_MS);
    try {
      const created = await createLeadDiscoveryRun({
        target_customer: form.target_customer,
        region: form.region || null,
        offer_profile_id: form.offer_profile_id,
        icp_profile_id: form.icp_profile_id || null,
        requested_count: Number(form.requested_count) || 10,
        min_score: Number(form.min_score) || 0,
      });
      const detail = await runLeadDiscoveryPipeline(created.id);
      setRun(detail);
      await refreshPastRuns();
      showToast(
        `${detail.qualified_leads} qualifiziert, ${detail.needs_review_leads} zu prüfen von ${detail.found_candidates} gefunden.`,
        "success"
      );
      // Scroll the result into view once it's rendered — a short delay
      // lets React commit the new DOM first. `scrollIntoView({behavior:
      // "smooth"})` already degrades to an instant jump under
      // `prefers-reduced-motion` via the global `scroll-behavior: auto`
      // override in globals.css.
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Unerwarteter Fehler.";
      setError(message);
      showToast(message, "error");
    } finally {
      if (searchStepTimer.current) clearInterval(searchStepTimer.current);
      setSubmitting(false);
    }
  }

  async function handleCreateDrafts() {
    if (!run) return;
    setCreatingDrafts(true);
    setError(null);
    try {
      const updated = await createLeadDiscoveryDrafts(run.id);
      setRun(updated);
      showToast("Drafts für qualifizierte Leads wurden vorbereitet.", "success");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Drafts konnten nicht erstellt werden.";
      setError(message);
      showToast(message, "error");
    } finally {
      setCreatingDrafts(false);
    }
  }

  async function handleAddToQueue(candidateId: string) {
    if (!run) return;
    setBusyCandidateId(candidateId);
    setError(null);
    try {
      const response = await addLeadDiscoveryCandidateToQueue(run.id, candidateId);
      setRun(response.run);
      showToast("Zur Review Queue hinzugefügt.", "success");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Konnte nicht zur Queue hinzugefügt werden.";
      setError(message);
      showToast(message, "error");
    } finally {
      setBusyCandidateId(null);
    }
  }

  async function handleShowRun(runId: string) {
    setError(null);
    try {
      const detail = await getLeadDiscoveryRun(runId);
      setRun(detail);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 60);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Lauf konnte nicht geladen werden.");
    }
  }

  return (
    <RequireRole
      allowedRoles={["admin", "sales", "reviewer"]}
      deniedMessage="Nur Admin, Sales und Reviewer haben Zugriff auf den Lead Finder."
    >
      <div id="lead-finder" className="space-y-10 scroll-mt-20">
        {!embedded ? (
          <div>
            <h1 className="text-4xl font-bold tracking-tight text-muted">
              Wen willst du finden?
            </h1>
            <p className="mt-3 max-w-2xl text-base text-muted/55">
              Zielgruppe, Region und Angebot eingeben — der Copilot sucht Kandidaten,
              analysiert deren Website, bewertet den Fit und erstellt nur prüfbare
              Drafts. Ergebnisse landen als Vorschlag zur menschlichen Prüfung, nie
              als automatischer Versand.
            </p>
          </div>
        ) : null}

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-y border-muted/12 py-3 text-xs text-muted/55">
          <span>Nur öffentliche Daten</span>
          <span aria-hidden="true">·</span>
          <span>Kein LinkedIn Scraping, keine Captcha-Umgehung</span>
          <span aria-hidden="true">·</span>
          <span>Do-not-contact geprüft</span>
          <span aria-hidden="true">·</span>
          <span>Nur Entwürfe — kein automatischer Versand</span>
        </div>

        <Card variant="framed">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-muted">Suche starten</h2>
              <p className="mt-2 max-w-xl text-sm text-muted/55">
                Der Copilot sucht Kandidaten, analysiert deren Website, bewertet den
                Fit und erstellt nur prüfbare Drafts.
              </p>
            </div>
            {providerStatus ? (
              <div className="flex flex-none flex-col items-end gap-1">
                <Badge tone={providerStatus.real_search_enabled ? "warning" : "positive"}>
                  {PROVIDER_LABEL[providerStatus.provider] ?? providerStatus.provider} aktiv
                  {providerStatus.real_search_enabled ? " · echte Suche aktiv" : " · Safe Mode"}
                </Badge>
                {providerStatus.warnings.map((w) => (
                  <span key={w} className="text-right text-xs text-amber-300">
                    {w}
                  </span>
                ))}
              </div>
            ) : null}
          </div>

          <form className="mt-10 grid gap-x-8 gap-y-6 sm:grid-cols-2" onSubmit={handleSubmit}>
            <Input
              label="Zielbranche / Kundentyp *"
              required
              value={form.target_customer}
              onChange={(e) => setForm({ ...form, target_customer: e.target.value })}
              placeholder="z. B. SaaS-Anbieter, Logistikunternehmen, Handwerksbetriebe"
            />
            <Input
              label="Ort / Region"
              value={form.region}
              onChange={(e) => setForm({ ...form, region: e.target.value })}
              placeholder="z. B. Berlin, DACH-Region, bundesweit"
            />
            <Select
              label="Angebot *"
              value={form.offer_profile_id}
              onChange={(e) => setForm({ ...form, offer_profile_id: e.target.value })}
              options={[
                { value: "", label: loadingProfiles ? "Lädt…" : "Bitte auswählen" },
                ...offers.map((o) => ({ value: o.id, label: o.name })),
              ]}
              required
            />
            <Select
              label="ICP Profil (optional)"
              value={form.icp_profile_id}
              onChange={(e) => setForm({ ...form, icp_profile_id: e.target.value })}
              options={[
                { value: "", label: "Ohne ICP-Filter" },
                ...icps.map((i) => ({ value: i.id, label: i.name })),
              ]}
            />
            <Input
              label="Anzahl Leads"
              type="number"
              min={1}
              max={50}
              value={form.requested_count}
              onChange={(e) => setForm({ ...form, requested_count: e.target.value })}
            />
            <Input
              label="Mindestscore"
              type="number"
              min={0}
              max={100}
              value={form.min_score}
              onChange={(e) => setForm({ ...form, min_score: e.target.value })}
              hint="Ab diesem Qualifikations-Score gilt ein Lead als qualifiziert."
            />
            {!loadingProfiles && offers.length === 0 ? (
              <p className="text-sm text-amber-300 sm:col-span-2">
                Kein Angebot vorhanden.{" "}
                <Link href="/sales-strategy/offers" className="underline hover:no-underline">
                  Erst ein Angebot anlegen →
                </Link>
              </p>
            ) : null}
            <div className="flex flex-col gap-4 pt-4 sm:col-span-2">
              <Button
                type="submit"
                size="lg"
                loading={submitting}
                disabled={offers.length === 0}
                className="w-fit"
              >
                Firmen finden &amp; Websites analysieren
              </Button>
              {submitting ? (
                <div
                  className="flex flex-wrap items-center gap-x-6 gap-y-2 animate-fade-in"
                  role="status"
                  aria-live="polite"
                >
                  {SEARCH_STEPS.map((label, index) => {
                    const active = index === searchStep;
                    const done = index < searchStep;
                    return (
                      <div key={label} className="flex items-center gap-2">
                        <span
                          className={`h-1.5 w-1.5 flex-none rounded-full ${
                            done || active ? "bg-muted" : "bg-muted/20"
                          } ${active ? "motion-safe:animate-pulse-soft" : ""}`}
                          aria-hidden="true"
                        />
                        <span className={`mono-label ${done || active ? "text-muted" : "text-muted/30"}`}>
                          {label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : null}
            </div>
          </form>
          {error ? <p className="mt-3 text-sm text-rose-400">{error}</p> : null}
        </Card>

        {run ? (
          <div ref={resultRef} className="scroll-mt-20 space-y-10">
            <Card title={`Ergebnis: ${run.name}`}>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={RUN_STATUS_TONE[run.status] ?? "neutral"}>
                  {RUN_STATUS_LABEL[run.status] ?? run.status}
                </Badge>
              </div>

              {/* Stat strip — big bold numbers over a hairline, echoing an
                  editorial "by the numbers" section instead of a plain
                  inline summary sentence. */}
              <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-6 sm:grid-cols-3 lg:grid-cols-6">
                {[
                  { value: run.found_candidates, label: "Gefunden" },
                  { value: run.analyzed_websites, label: "Websites analysiert" },
                  { value: run.qualified_leads, label: "Qualifiziert" },
                  { value: run.needs_review_leads, label: "Zu prüfen" },
                  { value: run.rejected_leads, label: "Abgelehnt" },
                  { value: run.created_drafts, label: "Drafts erstellt" },
                ].map((stat) => (
                  <div key={stat.label}>
                    <p className="text-3xl font-black tracking-tight text-muted">{stat.value}</p>
                    <div className="mt-2 border-t border-dashed border-muted/25" />
                    <p className="mt-2 text-xs text-muted/55">{stat.label}</p>
                  </div>
                ))}
              </div>
              {run.warnings.length > 0 || run.errors.length > 0 ? (
                <details className="mt-3 border-t border-muted/12 pt-3" open={run.errors.length > 0}>
                  <summary className="cursor-pointer list-none text-xs font-semibold uppercase tracking-wide text-muted/40 hover:text-muted">
                    Run-Diagnose ({run.warnings.length + run.errors.length})
                  </summary>
                  <div className="mt-2 space-y-2">
                    {run.warnings.length > 0 ? (
                      <div className="border-l-4 border-l-amber-500 py-1 pl-3 text-xs text-muted/80">
                        {run.warnings.map((w) => (
                          <p key={w}>• {w}</p>
                        ))}
                      </div>
                    ) : null}
                    {run.errors.length > 0 ? (
                      <div className="border-l-4 border-l-rose-500 py-1 pl-3 text-xs text-rose-300">
                        {run.errors.map((e) => (
                          <p key={e}>• {e}</p>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </details>
              ) : null}
              {run.status === "completed" ? (
                <div className="mt-3">
                  <Button variant="secondary" loading={creatingDrafts} onClick={handleCreateDrafts}>
                    Drafts für qualifizierte Leads erstellen
                  </Button>
                  <p className="mt-1 text-xs text-muted/55">
                    Erstellt nur Entwürfe für Leads, die bereits in der Review Queue
                    stehen — kein Versand, keine externe Draft-Erstellung.
                  </p>
                </div>
              ) : null}
            </Card>

            <div>
              <div className="flex flex-wrap items-end justify-between gap-4">
                <h2 className="text-xl font-bold tracking-tight text-muted">Gefundene Firmen</h2>
                {run.candidates.length > 0 ? (
                  <p className="text-xs text-muted/55">
                    {visibleCandidates.length} von {run.candidates.length} angezeigt
                  </p>
                ) : null}
              </div>

              {run.candidates.length > 0 ? (
                <div className="mt-4 flex flex-wrap items-center gap-4 border-b border-muted/12 pb-4">
                  <div className="flex flex-wrap gap-2">
                    {(Object.keys(CANDIDATE_FILTER_LABEL) as CandidateFilter[]).map((filter) => (
                      <button
                        key={filter}
                        type="button"
                        onClick={() => setCandidateFilter(filter)}
                        className={`border px-3 py-1.5 text-xs font-bold uppercase tracking-wide transition-colors ${
                          candidateFilter === filter
                            ? "border-muted bg-muted text-canvas"
                            : "border-muted/20 text-muted/55 hover:border-muted hover:text-muted"
                        }`}
                      >
                        {CANDIDATE_FILTER_LABEL[filter]}
                      </button>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={() => setSortByScore((v) => !v)}
                    className={`border px-3 py-1.5 text-xs font-bold uppercase tracking-wide transition-colors ${
                      sortByScore
                        ? "border-muted bg-muted text-canvas"
                        : "border-muted/20 text-muted/55 hover:border-muted hover:text-muted"
                    }`}
                  >
                    Nach Score sortiert
                  </button>
                  <input
                    type="search"
                    value={candidateSearch}
                    onChange={(e) => setCandidateSearch(e.target.value)}
                    placeholder="Suche in Ergebnissen…"
                    aria-label="Suche in Ergebnissen"
                    className="min-w-[200px] flex-1 border border-muted/20 bg-canvas px-3 py-1.5 text-sm text-muted outline-none transition-colors placeholder:text-muted/40 focus:border-muted"
                  />
                </div>
              ) : null}

              <div className="mt-4 space-y-3">
                {run.candidates.length === 0 ? (
                  <EmptyState
                    title="Keine Kandidaten gefunden"
                    description="Zielgruppe oder Region anpassen und erneut versuchen."
                  />
                ) : visibleCandidates.length === 0 ? (
                  <EmptyState
                    title="Keine Treffer für diesen Filter"
                    description="Filter oder Suchbegriff zurücksetzen, um alle gefundenen Firmen zu sehen."
                    action={
                      <Button
                        variant="secondary"
                        onClick={() => {
                          setCandidateFilter("all");
                          setCandidateSearch("");
                        }}
                      >
                        Filter zurücksetzen
                      </Button>
                    }
                  />
                ) : (
                  visibleCandidates.map((candidate, index) => (
                    <Reveal key={candidate.candidate_id} delayMs={Math.min(index, 6) * 60}>
                      <CandidateRow
                        candidate={candidate}
                        expanded={expandedCandidateId === candidate.candidate_id}
                        onToggle={() =>
                          setExpandedCandidateId(
                            expandedCandidateId === candidate.candidate_id
                              ? null
                              : candidate.candidate_id
                          )
                        }
                        onAddToQueue={() => handleAddToQueue(candidate.candidate_id)}
                        busy={busyCandidateId === candidate.candidate_id}
                      />
                    </Reveal>
                  ))
                )}
              </div>
            </div>
          </div>
        ) : null}

        <div id="letzte-runs" className="scroll-mt-20">
          <h2 className="mb-4 text-xl font-bold tracking-tight text-muted">Letzte Runs</h2>
          {loadingProfiles ? (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              <SkeletonRunCard />
              <SkeletonRunCard />
              <SkeletonRunCard />
            </div>
          ) : pastRuns.length === 0 ? (
            <EmptyState
              title="Noch keine Lead Finder Läufe"
              description="Starte oben deine erste Suche."
            />
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {pastRuns.map((pastRun, index) => {
                const nextStep =
                  pastRun.status === "pending"
                    ? "Analyse starten"
                    : pastRun.status === "running"
                      ? "Läuft …"
                      : pastRun.status === "failed"
                        ? "Fehler prüfen"
                        : pastRun.created_drafts > 0
                          ? "Drafts prüfen"
                          : pastRun.qualified_leads > 0
                            ? "Drafts erstellen"
                            : pastRun.needs_review_leads > 0
                              ? "Kandidaten zu prüfen ansehen"
                              : "Ergebnis ansehen";
                return (
                  <Reveal key={pastRun.id} delayMs={Math.min(index, 6) * 60}>
                  <Card interactive className="flex flex-col justify-between">
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-semibold text-muted">{pastRun.name}</p>
                        <Badge tone={RUN_STATUS_TONE[pastRun.status] ?? "neutral"}>
                          {RUN_STATUS_LABEL[pastRun.status] ?? pastRun.status}
                        </Badge>
                      </div>
                      <p className="mt-1 text-xs text-muted/55">
                        {pastRun.target_customer}
                        {pastRun.region ? ` · ${pastRun.region}` : ""}
                      </p>
                      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-muted/55">
                        <div>
                          <dt className="text-muted/40">Gefunden</dt>
                          <dd className="font-medium text-muted">{pastRun.found_candidates}</dd>
                        </div>
                        <div>
                          <dt className="text-muted/40">Qualifiziert</dt>
                          <dd className="font-medium text-muted">{pastRun.qualified_leads}</dd>
                        </div>
                      </dl>
                      {pastRun.warnings.length > 0 ? (
                        <p className="mt-2 text-xs text-amber-300">
                          {pastRun.warnings.length} Warning(en)
                        </p>
                      ) : null}
                    </div>
                    <div className="mt-4 flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-muted/55">
                        Nächster Schritt: {nextStep}
                      </span>
                      <button
                        type="button"
                        className="text-xs font-semibold text-muted underline underline-offset-2 hover:text-muted/55"
                        onClick={() => handleShowRun(pastRun.id)}
                      >
                        Anzeigen
                      </button>
                    </div>
                  </Card>
                  </Reveal>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </RequireRole>
  );
}
