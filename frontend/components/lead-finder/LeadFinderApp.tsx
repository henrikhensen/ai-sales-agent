"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
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
  return (
    <Card className={blocked ? "border-rose-200" : undefined}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-slate-900">
              {candidate.company_name ?? "Unbekannte Firma"}
            </p>
            {candidate.company_website_url ? (
              <a
                href={candidate.company_website_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-brand-600 underline hover:no-underline"
              >
                Website →
              </a>
            ) : null}
          </div>
          <p className="mt-0.5 text-xs text-slate-500">
            {[candidate.industry, candidate.location].filter(Boolean).join(" · ") || "—"}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={WEBSITE_QUALITY_TONE[candidate.website_quality_level ?? ""] ?? "neutral"}>
            Website: {WEBSITE_QUALITY_LABEL[candidate.website_quality_level ?? ""] ?? "—"}
          </Badge>
          {candidate.qualification_score !== null ? (
            <Badge
              tone={QUALIFICATION_STATUS_TONE[candidate.qualification_status ?? ""] ?? "neutral"}
            >
              Score {candidate.qualification_score} ·{" "}
              {QUALIFICATION_STATUS_LABEL[candidate.qualification_status ?? ""] ??
                candidate.qualification_status}
            </Badge>
          ) : (
            <Badge tone="neutral">Noch nicht qualifiziert</Badge>
          )}
          {blocked ? <Badge tone="negative">Do-not-contact</Badge> : null}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <Badge tone={DRAFT_STATUS_TONE[candidate.draft_status]}>
          Draft: {DRAFT_STATUS_LABEL[candidate.draft_status]}
        </Badge>
        <Badge tone={candidate.in_outreach_queue ? "positive" : "neutral"}>
          {candidate.in_outreach_queue ? "In Review Queue" : "Nicht in Queue"}
        </Badge>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button variant="secondary" onClick={onToggle}>
          {expanded ? "Details ausblenden" : "Details ansehen"}
        </Button>
        {candidate.email_draft_id ? (
          <Link
            href="/crm"
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50"
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

      {expanded ? (
        <div className="mt-4 space-y-3 border-t border-slate-100 pt-3 text-sm">
          {candidate.fit_summary ? (
            <p className="text-slate-700">{candidate.fit_summary}</p>
          ) : null}
          {candidate.disqualification_reason ? (
            <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
              Ablehnungsgrund: {candidate.disqualification_reason}
            </p>
          ) : null}
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <p className="text-xs font-semibold text-slate-500">Warum geeignet</p>
              {candidate.positive_signals.length === 0 ? (
                <p className="text-xs text-slate-500">Keine Angaben.</p>
              ) : (
                <ul className="list-inside list-disc text-xs text-slate-700">
                  {candidate.positive_signals.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-500">Warum ungeeignet</p>
              {candidate.negative_signals.length === 0 ? (
                <p className="text-xs text-slate-500">Keine Angaben.</p>
              ) : (
                <ul className="list-inside list-disc text-xs text-rose-700">
                  {candidate.negative_signals.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          {candidate.missing_data.length > 0 ? (
            <div>
              <p className="text-xs font-semibold text-slate-500">
                Fehlende Daten für diese Bewertung
              </p>
              <ul className="list-inside list-disc text-xs text-slate-700">
                {candidate.missing_data.map((m) => (
                  <li key={m}>{m}</li>
                ))}
              </ul>
            </div>
          ) : null}
          <div>
            <p className="text-xs font-semibold text-slate-500">
              Gefundene Probleme auf der Website
            </p>
            {candidate.website_quality_reasons.length === 0 ? (
              <p className="text-xs text-slate-500">Keine Angaben.</p>
            ) : (
              <ul className="list-inside list-disc text-xs text-slate-700">
                {candidate.website_quality_reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            )}
          </div>
          {candidate.warnings.length > 0 ? (
            <div>
              <p className="text-xs font-semibold text-amber-700">Warnings</p>
              <ul className="list-inside list-disc text-xs text-amber-800">
                {candidate.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </Card>
  );
}

interface LeadFinderAppProps {
  /** Renders a shorter intro (no page-level H1) when embedded on a page
   * that already has its own hero, e.g. the home page. */
  embedded?: boolean;
}

export function LeadFinderApp({ embedded = false }: LeadFinderAppProps) {
  const [offers, setOffers] = useState<OfferProfile[]>([]);
  const [icps, setIcps] = useState<ICPProfile[]>([]);
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [loadingProfiles, setLoadingProfiles] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<LeadDiscoveryRunDetail | null>(null);
  const [pastRuns, setPastRuns] = useState<LeadDiscoveryRun[]>([]);
  const [expandedCandidateId, setExpandedCandidateId] = useState<string | null>(null);
  const [busyCandidateId, setBusyCandidateId] = useState<string | null>(null);
  const [creatingDrafts, setCreatingDrafts] = useState(false);
  const [providerStatus, setProviderStatus] = useState<LeadSourcingProviderStatus | null>(
    null
  );

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
    setError(null);
    setRun(null);
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
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
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
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Drafts konnten nicht erstellt werden."
      );
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
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Konnte nicht zur Queue hinzugefügt werden."
      );
    } finally {
      setBusyCandidateId(null);
    }
  }

  async function handleShowRun(runId: string) {
    setError(null);
    try {
      const detail = await getLeadDiscoveryRun(runId);
      setRun(detail);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Lauf konnte nicht geladen werden.");
    }
  }

  return (
    <RequireRole
      allowedRoles={["admin", "sales", "reviewer"]}
      deniedMessage="Nur Admin, Sales und Reviewer haben Zugriff auf den Lead Finder."
    >
      <div id="lead-finder" className="space-y-6 scroll-mt-20">
        {!embedded ? (
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              Wen willst du finden?
            </h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-600">
              Zielgruppe, Region und Angebot eingeben — der Copilot sucht Kandidaten,
              analysiert deren Website, bewertet den Fit und erstellt nur prüfbare
              Drafts. Ergebnisse landen als Vorschlag zur menschlichen Prüfung, nie
              als automatischer Versand.
            </p>
          </div>
        ) : null}

        <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <ul className="list-inside list-disc space-y-0.5">
            <li>Nur öffentlich sichtbare Firmen- und Kontaktinformationen.</li>
            <li>Kein LinkedIn Scraping, kein Scraping hinter Login, keine Captcha-Umgehung.</li>
            <li>Keine persönlichen E-Mail-Adressen werden erraten.</li>
            <li>Do-not-contact wird für jeden Kandidaten geprüft.</li>
            <li>Drafts werden nur vorbereitet — kein automatischer Versand, kein Send-Button.</li>
          </ul>
        </div>

        <Card
          title="Suche starten"
          description="Der Copilot sucht Kandidaten, analysiert deren Website, bewertet den Fit und erstellt nur prüfbare Drafts."
        >
          {providerStatus ? (
            <div className="mb-4 flex flex-wrap items-center gap-2">
              <Badge tone={providerStatus.real_search_enabled ? "warning" : "positive"}>
                Firmensuche: {PROVIDER_LABEL[providerStatus.provider] ?? providerStatus.provider}
                {providerStatus.real_search_enabled ? " (echte Suche aktiv)" : " (Safe Mode)"}
              </Badge>
              {providerStatus.warnings.map((w) => (
                <span key={w} className="text-xs text-amber-700">
                  {w}
                </span>
              ))}
            </div>
          ) : null}
          <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleSubmit}>
            <Input
              label="Zielbranche / Kundentyp *"
              required
              value={form.target_customer}
              onChange={(e) => setForm({ ...form, target_customer: e.target.value })}
              placeholder="z. B. Software, Logistik, Handel"
            />
            <Input
              label="Ort / Region"
              value={form.region}
              onChange={(e) => setForm({ ...form, region: e.target.value })}
              placeholder="z. B. Berlin, Deutschland"
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
                { value: "", label: "Keins" },
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
              <p className="text-sm text-amber-700 sm:col-span-2">
                Kein Angebot vorhanden.{" "}
                <Link href="/sales-strategy/offers" className="underline hover:no-underline">
                  Erst ein Angebot anlegen →
                </Link>
              </p>
            ) : null}
            <div className="sm:col-span-2">
              <Button type="submit" loading={submitting} disabled={offers.length === 0}>
                Firmen finden &amp; Websites analysieren
              </Button>
            </div>
          </form>
          {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
        </Card>

        {run ? (
          <>
            <Card title={`Ergebnis: ${run.name}`}>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={RUN_STATUS_TONE[run.status] ?? "neutral"}>
                  {RUN_STATUS_LABEL[run.status] ?? run.status}
                </Badge>
                <span className="text-sm text-slate-600">
                  {run.found_candidates} gefunden · {run.analyzed_websites} Websites
                  analysiert · {run.qualified_leads} qualifiziert ·{" "}
                  {run.needs_review_leads} zu prüfen · {run.rejected_leads} abgelehnt ·{" "}
                  {run.created_drafts} Drafts erstellt
                </span>
              </div>
              {run.warnings.length > 0 ? (
                <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  {run.warnings.map((w) => (
                    <p key={w}>• {w}</p>
                  ))}
                </div>
              ) : null}
              {run.errors.length > 0 ? (
                <div className="mt-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                  {run.errors.map((e) => (
                    <p key={e}>• {e}</p>
                  ))}
                </div>
              ) : null}
              {run.status === "completed" ? (
                <div className="mt-3">
                  <Button variant="secondary" loading={creatingDrafts} onClick={handleCreateDrafts}>
                    Drafts für qualifizierte Leads erstellen
                  </Button>
                  <p className="mt-1 text-xs text-slate-500">
                    Erstellt nur Entwürfe für Leads, die bereits in der Review Queue
                    stehen — kein Versand, keine externe Draft-Erstellung.
                  </p>
                </div>
              ) : null}
            </Card>

            <div>
              <h2 className="mb-3 text-lg font-semibold tracking-tight text-slate-900">
                Gefundene Firmen
              </h2>
              <div className="space-y-3">
                {run.candidates.length === 0 ? (
                  <Card>
                    <p className="text-sm text-slate-500">
                      Keine Kandidaten gefunden — Zielgruppe oder Region anpassen und
                      erneut versuchen.
                    </p>
                  </Card>
                ) : (
                  run.candidates.map((candidate) => (
                    <CandidateRow
                      key={candidate.candidate_id}
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
                  ))
                )}
              </div>
            </div>
          </>
        ) : null}

        <div id="letzte-runs" className="scroll-mt-20">
          <h2 className="mb-3 text-lg font-semibold tracking-tight text-slate-900">
            Letzte Runs
          </h2>
          {pastRuns.length === 0 ? (
            <Card>
              <p className="text-sm text-slate-500">
                Noch keine Lead Finder Läufe — starte oben deine erste Suche.
              </p>
            </Card>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {pastRuns.map((pastRun) => {
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
                  <Card key={pastRun.id} className="flex flex-col justify-between">
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-semibold text-slate-900">
                          {pastRun.name}
                        </p>
                        <Badge tone={RUN_STATUS_TONE[pastRun.status] ?? "neutral"}>
                          {RUN_STATUS_LABEL[pastRun.status] ?? pastRun.status}
                        </Badge>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {pastRun.target_customer}
                        {pastRun.region ? ` · ${pastRun.region}` : ""}
                      </p>
                      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
                        <div>
                          <dt className="text-slate-400">Gefunden</dt>
                          <dd className="font-medium text-slate-900">
                            {pastRun.found_candidates}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-slate-400">Qualifiziert</dt>
                          <dd className="font-medium text-slate-900">
                            {pastRun.qualified_leads}
                          </dd>
                        </div>
                      </dl>
                      {pastRun.warnings.length > 0 ? (
                        <p className="mt-2 text-xs text-amber-700">
                          {pastRun.warnings.length} Warning(en)
                        </p>
                      ) : null}
                    </div>
                    <div className="mt-4 flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-slate-500">
                        Nächster Schritt: {nextStep}
                      </span>
                      <button
                        type="button"
                        className="text-xs font-semibold text-brand-600 underline hover:no-underline"
                        onClick={() => handleShowRun(pastRun.id)}
                      >
                        Anzeigen
                      </button>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </RequireRole>
  );
}
