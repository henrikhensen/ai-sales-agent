"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import {
  ApiError,
  getICPProfiles,
  getLeadQualificationDashboard,
  getLeadQualificationResults,
  getLeadQualificationStatus,
  getOfferProfiles,
  reviewQualificationResult,
  startLeadQualificationRun,
} from "@/lib/api";
import { canManageLeadQualification, canReviewQualificationResult } from "@/lib/roles";
import type {
  ICPProfile,
  LeadQualificationResult,
  LeadQualificationStatus,
  OfferProfile,
  QualificationDashboardResponse,
  QualificationSourceType,
} from "@/lib/types";

const LEVEL_TONE: Record<string, "positive" | "info" | "warning" | "negative" | "neutral"> = {
  excellent: "positive",
  good: "positive",
  medium: "info",
  weak: "warning",
  not_fit: "negative",
};

const STATUS_TONE: Record<string, "positive" | "info" | "warning" | "negative" | "neutral"> = {
  qualified: "positive",
  priority: "positive",
  needs_review: "warning",
  disqualified: "negative",
  blocked: "negative",
  duplicate: "neutral",
};

const SOURCE_OPTIONS: { value: QualificationSourceType; label: string }[] = [
  { value: "lead_candidate", label: "Lead Candidates" },
  { value: "crm_lead", label: "CRM Leads" },
  { value: "mixed", label: "Gemischt (Candidates + Leads)" },
];

function idsFromText(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((id) => id.trim())
    .filter(Boolean);
}

export default function LeadQualificationPage() {
  const { currentUser } = useAuth();
  const canManage = canManageLeadQualification(currentUser);
  const canReview = canReviewQualificationResult(currentUser);

  const [status, setStatus] = useState<LeadQualificationStatus | null>(null);
  const [dashboard, setDashboard] = useState<QualificationDashboardResponse | null>(null);
  const [icpProfiles, setIcpProfiles] = useState<ICPProfile[]>([]);
  const [offerProfiles, setOfferProfiles] = useState<OfferProfile[]>([]);
  const [results, setResults] = useState<LeadQualificationResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    source_type: "lead_candidate" as QualificationSourceType,
    ids_text: "",
    icp_profile_id: "",
    offer_profile_id: "",
    min_score: "",
    dry_run: false,
  });
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [runNote, setRunNote] = useState<string | null>(null);

  const [expandedResultId, setExpandedResultId] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusResponse, dashboardResponse, icpResponse, offerResponse, resultsResponse] =
        await Promise.all([
          getLeadQualificationStatus(),
          getLeadQualificationDashboard(),
          getICPProfiles(true),
          getOfferProfiles(true),
          getLeadQualificationResults(),
        ]);
      setStatus(statusResponse);
      setDashboard(dashboardResponse);
      setIcpProfiles(icpResponse.items);
      setOfferProfiles(offerResponse.items);
      setResults(resultsResponse.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  async function handleStartRun(event: React.FormEvent) {
    event.preventDefault();
    setRunning(true);
    setRunError(null);
    setRunNote(null);
    const ids = idsFromText(form.ids_text);
    try {
      const result = await startLeadQualificationRun({
        source_type: form.source_type,
        lead_candidate_ids: form.source_type !== "crm_lead" ? ids : undefined,
        lead_ids: form.source_type !== "lead_candidate" ? ids : undefined,
        icp_profile_id: form.icp_profile_id || null,
        offer_profile_id: form.offer_profile_id || null,
        min_score: form.min_score ? Number(form.min_score) : null,
        dry_run: form.dry_run,
      });
      setRunNote(
        `Run ${result.dry_run ? "(Dry Run) " : ""}abgeschlossen: ${result.run.total_items} bewertet, ` +
          `${result.run.qualified_count} qualified, ${result.run.priority_count} priority, ` +
          `Ø ${result.run.average_score?.toFixed(1) ?? "—"}.`
      );
      await loadAll();
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setRunning(false);
    }
  }

  async function handleReview(
    resultId: string,
    qualificationStatus: "qualified" | "priority" | "needs_review" | "disqualified"
  ) {
    setReviewError(null);
    try {
      await reviewQualificationResult(resultId, { qualification_status: qualificationStatus });
      await loadAll();
    } catch (err) {
      setReviewError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Lead Qualification</h1>
          <p className="mt-1 text-sm text-slate-600">
            Bewertet und priorisiert Leads und Candidates anhand von ICP und
            Offer — als Entscheidungshilfe für den nächsten Schritt.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Nächster Schritt nach der Qualifizierung:{" "}
            <a href="/outreach" className="underline hover:no-underline">
              Outreach Queue
            </a>
            .
          </p>
        </div>

        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <ul className="list-inside list-disc space-y-1">
            <li>Qualification priorisiert Leads, sendet aber keine E-Mails.</li>
            <li>Scores sind Entscheidungshilfen, keine Garantie.</li>
            <li>Do-not-contact blockiert Leads immer.</li>
            <li>Duplicates sollen nicht doppelt kontaktiert werden.</li>
            <li>Schlechter Fit sollte nicht kontaktiert werden.</li>
            <li>Human Review bleibt erforderlich.</li>
            <li>Mock Provider ist Standard.</li>
          </ul>
        </div>

        {status ? (
          <Card title="Status">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={status.enabled ? "positive" : "neutral"}>
                {status.enabled ? "aktiv" : "deaktiviert"}
              </Badge>
              <Badge tone={status.use_llm ? "warning" : "positive"}>
                {status.use_llm ? "LLM Advisor aktiv" : "Regelbasiert (kein LLM)"}
              </Badge>
              <Badge tone={status.llm_real_calls_enabled ? "warning" : "positive"}>
                {status.llm_real_calls_enabled ? "Echte LLM Calls möglich" : "Safe Mode (Mock)"}
              </Badge>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600 sm:grid-cols-3">
              <p>Min Score: {status.default_min_score}</p>
              <p>Priority Score: {status.priority_score}</p>
              <p>Disqualify Score: {status.disqualify_score}</p>
            </dl>
            {status.warnings.length > 0 ? (
              <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                {status.warnings.map((w) => (
                  <p key={w}>{w}</p>
                ))}
              </div>
            ) : null}
          </Card>
        ) : null}

        {dashboard ? (
          <Card title="Dashboard">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-6">
              <div>
                <p className="text-xs text-slate-500">Qualified</p>
                <p className="text-lg font-semibold text-slate-900">
                  {dashboard.total_qualified}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Priority</p>
                <p className="text-lg font-semibold text-slate-900">
                  {dashboard.total_priority}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Needs Review</p>
                <p className="text-lg font-semibold text-slate-900">
                  {dashboard.total_needs_review}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Disqualified</p>
                <p className="text-lg font-semibold text-slate-900">
                  {dashboard.total_disqualified}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Blocked</p>
                <p className="text-lg font-semibold text-slate-900">
                  {dashboard.total_blocked}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Ø Score</p>
                <p className="text-lg font-semibold text-slate-900">
                  {dashboard.average_score?.toFixed(1) ?? "—"}
                </p>
              </div>
            </div>
            {dashboard.top_recommended_leads.length > 0 ? (
              <div className="mt-4">
                <p className="text-xs font-semibold uppercase text-slate-500">
                  Top Recommended
                </p>
                <ul className="mt-1 space-y-1 text-sm text-slate-700">
                  {dashboard.top_recommended_leads.map((r) => (
                    <li key={r.id} className="flex items-center gap-2">
                      <Badge tone={STATUS_TONE[r.qualification_status] ?? "neutral"}>
                        {r.qualification_score}
                      </Badge>
                      {r.fit_summary}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            {dashboard.warnings.length > 0 ? (
              <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                {dashboard.warnings.map((w) => (
                  <p key={w}>{w}</p>
                ))}
              </div>
            ) : null}
          </Card>
        ) : null}

        {canManage ? (
          <Card title="Qualification Run starten">
            <form className="space-y-4" onSubmit={handleStartRun}>
              <Select
                label="Source"
                value={form.source_type}
                options={SOURCE_OPTIONS}
                onChange={(e) =>
                  setForm({ ...form, source_type: e.target.value as QualificationSourceType })
                }
              />
              <Textarea
                label="IDs (Kandidaten- oder Lead-IDs, kommagetrennt oder eine pro Zeile)"
                value={form.ids_text}
                onChange={(e) => setForm({ ...form, ids_text: e.target.value })}
                hint="Leer lassen, um automatisch alle offenen Einträge zu bewerten (max. 50)."
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Select
                  label="ICP Profil (optional)"
                  value={form.icp_profile_id}
                  options={[
                    { value: "", label: "Keins" },
                    ...icpProfiles.map((p) => ({ value: p.id, label: p.name })),
                  ]}
                  onChange={(e) => setForm({ ...form, icp_profile_id: e.target.value })}
                />
                <Select
                  label="Offer Profil (optional)"
                  value={form.offer_profile_id}
                  options={[
                    { value: "", label: "Keins" },
                    ...offerProfiles.map((p) => ({ value: p.id, label: p.name })),
                  ]}
                  onChange={(e) => setForm({ ...form, offer_profile_id: e.target.value })}
                />
                <Input
                  label="Min Score (optional)"
                  type="number"
                  min={0}
                  max={100}
                  value={form.min_score}
                  onChange={(e) => setForm({ ...form, min_score: e.target.value })}
                />
                <label className="flex items-center gap-2 pt-6 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    checked={form.dry_run}
                    onChange={(e) => setForm({ ...form, dry_run: e.target.checked })}
                  />
                  Dry Run (keine Pipeline-Änderungen)
                </label>
              </div>
              <Button type="submit" loading={running}>
                Run starten
              </Button>
              {runError ? <p className="text-sm text-rose-600">{runError}</p> : null}
              {runNote ? <p className="text-sm text-slate-600">{runNote}</p> : null}
            </form>
          </Card>
        ) : null}

        <Card title="Qualification Results">
          {loading ? (
            <p className="text-sm text-slate-500">Ergebnisse werden geladen…</p>
          ) : error ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </div>
          ) : results.length > 0 ? (
            <div className="space-y-3">
              {reviewError ? <p className="text-sm text-rose-600">{reviewError}</p> : null}
              {results.map((result) => {
                const isExpanded = expandedResultId === result.id;
                return (
                  <div
                    key={result.id}
                    className="rounded-lg border border-slate-200 bg-white px-4 py-3"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <button
                        type="button"
                        className="text-left"
                        onClick={() => setExpandedResultId(isExpanded ? null : result.id)}
                      >
                        <p className="text-sm font-semibold text-slate-900">
                          {result.fit_summary ?? "Qualification Result"}
                        </p>
                        <p className="text-xs text-slate-600">
                          Rank: {result.priority_rank ?? "—"} · Confidence:{" "}
                          {result.confidence_score ?? "—"}
                        </p>
                      </button>
                      <div className="flex flex-wrap gap-1">
                        <Badge tone={LEVEL_TONE[result.qualification_level] ?? "neutral"}>
                          {result.qualification_score} · {result.qualification_level}
                        </Badge>
                        <Badge tone={STATUS_TONE[result.qualification_status] ?? "neutral"}>
                          {result.qualification_status}
                        </Badge>
                        <Badge tone="neutral">{result.recommended_next_action}</Badge>
                      </div>
                    </div>

                    {isExpanded ? (
                      <div className="mt-3 space-y-2 border-t border-slate-100 pt-3 text-sm">
                        <p>
                          Do-not-contact: {result.do_not_contact_status} · Duplicate:{" "}
                          {result.duplicate_status} · Compliance: {result.compliance_status}
                        </p>
                        {result.recommended_outreach_angle ? (
                          <p>
                            <span className="font-medium">Outreach Angle: </span>
                            {result.recommended_outreach_angle}
                          </p>
                        ) : null}
                        {result.disqualification_reason ? (
                          <p className="text-rose-700">
                            {result.disqualification_reason}
                          </p>
                        ) : null}
                        {result.positive_signals.length > 0 ? (
                          <div>
                            <p className="text-xs font-semibold text-slate-500">
                              Positive Signals
                            </p>
                            <ul className="list-inside list-disc text-xs text-slate-700">
                              {result.positive_signals.map((s) => (
                                <li key={s}>{s}</li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        {result.negative_signals.length > 0 ? (
                          <div>
                            <p className="text-xs font-semibold text-rose-500">
                              Negative Signals
                            </p>
                            <ul className="list-inside list-disc text-xs text-rose-700">
                              {result.negative_signals.map((s) => (
                                <li key={s}>{s}</li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        {result.missing_data.length > 0 ? (
                          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                            <p className="font-semibold">Missing Data</p>
                            {result.missing_data.map((w) => (
                              <p key={w}>{w}</p>
                            ))}
                          </div>
                        ) : null}
                        <details className="text-xs text-slate-500">
                          <summary className="cursor-pointer">Score Breakdown</summary>
                          <pre className="mt-1 overflow-x-auto rounded bg-slate-50 p-2">
                            {JSON.stringify(result.score_breakdown, null, 2)}
                          </pre>
                        </details>
                        <div className="flex flex-wrap gap-3 pt-1">
                          {result.lead_id ? (
                            <a href="/crm" className="underline hover:no-underline">
                              CRM Lead öffnen
                            </a>
                          ) : null}
                          {result.company_id ? (
                            <a href="/crm" className="underline hover:no-underline">
                              CRM Company öffnen
                            </a>
                          ) : null}
                          {result.lead_candidate_id ? (
                            <a
                              href="/lead-sourcing"
                              className="underline hover:no-underline"
                            >
                              Candidate öffnen
                            </a>
                          ) : null}
                          <a
                            href="/workflows/sales"
                            className="underline hover:no-underline"
                          >
                            Sales Workflow manuell starten
                          </a>
                          {["qualified", "priority"].includes(result.qualification_status) &&
                          result.compliance_status !== "blocked" &&
                          result.duplicate_status !== "duplicate" ? (
                            <a
                              href={`/outreach?qualification_result_id=${encodeURIComponent(
                                result.id
                              )}`}
                              className="underline hover:no-underline"
                            >
                              Zur Outreach Queue hinzufügen
                            </a>
                          ) : null}
                        </div>
                        {canReview ? (
                          <div className="flex flex-wrap gap-2 pt-2">
                            <Button onClick={() => handleReview(result.id, "qualified")}>
                              Als geprüft markieren
                            </Button>
                            <Button
                              variant="secondary"
                              onClick={() => handleReview(result.id, "priority")}
                            >
                              Als priority bestätigen
                            </Button>
                            <Button
                              variant="ghost"
                              onClick={() => handleReview(result.id, "disqualified")}
                            >
                              Als disqualified markieren
                            </Button>
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Noch keine Qualification Results.</p>
          )}
        </Card>
      </div>
    </RequireAuth>
  );
}
