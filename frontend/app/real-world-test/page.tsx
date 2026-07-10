"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { RequireRole } from "@/components/auth/RequireRole";
import { QualityScoreBadge } from "@/components/quality/QualityScoreBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { JsonViewer } from "@/components/ui/JsonViewer";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import {
  abortRealWorldTestRun,
  ApiError,
  createRealWorldTestRun,
  getICPProfiles,
  getLeadCandidates,
  getOfferProfiles,
  getRealWorldTestRuns,
  listCrmLeads,
} from "@/lib/api";
import {
  canAbortRealWorldTestRun,
  canRunRealWorldTestRun,
  canViewRealWorldTestRuns,
} from "@/lib/roles";
import type {
  ICPProfile,
  Lead,
  LeadCandidate,
  OfferProfile,
  RealWorldTestRun,
  RealWorldTestRunMode,
} from "@/lib/types";

const STATUS_TONE: Record<string, "positive" | "warning" | "negative" | "neutral"> = {
  pending: "neutral",
  running: "warning",
  completed: "positive",
  blocked: "negative",
  failed: "negative",
  aborted: "neutral",
};

const MODE_OPTIONS: { value: RealWorldTestRunMode; label: string }[] = [
  { value: "safe", label: "safe (keine echte Website, kein echtes LLM)" },
  { value: "mock", label: "mock (echte Website möglich, LLM regulär konfiguriert)" },
  { value: "real_llm", label: "real_llm (erfordert LLM_ENABLE_REAL_CALLS=true)" },
];

export default function RealWorldTestModePage() {
  const { currentUser } = useAuth();
  const canRun = canRunRealWorldTestRun(currentUser);
  const canView = canViewRealWorldTestRuns(currentUser);
  const canAbort = canAbortRealWorldTestRun(currentUser);

  const [runs, setRuns] = useState<RealWorldTestRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RealWorldTestRun | null>(null);

  const [leadCandidates, setLeadCandidates] = useState<LeadCandidate[]>([]);
  const [crmLeads, setCrmLeads] = useState<Lead[]>([]);
  const [icpProfiles, setIcpProfiles] = useState<ICPProfile[]>([]);
  const [offerProfiles, setOfferProfiles] = useState<OfferProfile[]>([]);

  const [form, setForm] = useState({
    name: "",
    mode: "safe" as RealWorldTestRunMode,
    lead_candidate_id: "",
    lead_id: "",
    icp_profile_id: "",
    offer_profile_id: "",
    company_name: "",
    website_url: "",
    industry: "",
    product_or_service_offered: "",
    notes: "",
  });
  const [creating, setCreating] = useState(false);

  const loadRuns = useCallback(async () => {
    if (!canView) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getRealWorldTestRuns({ limit: 100 });
      setRuns(result.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, [canView]);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  useEffect(() => {
    if (!canRun) {
      return;
    }
    getLeadCandidates()
      .then((result) => setLeadCandidates(result.items))
      .catch(() => setLeadCandidates([]));
    listCrmLeads()
      .then(setCrmLeads)
      .catch(() => setCrmLeads([]));
    getICPProfiles(true)
      .then((result) => setIcpProfiles(result.items))
      .catch(() => setIcpProfiles([]));
    getOfferProfiles(true)
      .then((result) => setOfferProfiles(result.items))
      .catch(() => setOfferProfiles([]));
  }, [canRun]);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setCreating(true);
    setActionError(null);
    try {
      await createRealWorldTestRun({
        name: form.name,
        mode: form.mode,
        lead_candidate_id: form.lead_candidate_id || null,
        lead_id: form.lead_id || null,
        icp_profile_id: form.icp_profile_id || null,
        offer_profile_id: form.offer_profile_id || null,
        company_name: form.company_name || null,
        website_url: form.website_url || null,
        industry: form.industry || null,
        product_or_service_offered: form.product_or_service_offered || null,
        notes: form.notes || null,
      });
      setForm({
        name: "",
        mode: "safe",
        lead_candidate_id: "",
        lead_id: "",
        icp_profile_id: "",
        offer_profile_id: "",
        company_name: "",
        website_url: "",
        industry: "",
        product_or_service_offered: "",
        notes: "",
      });
      await loadRuns();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setCreating(false);
    }
  }

  async function handleAbort(runId: string) {
    setBusyId(runId);
    setActionError(null);
    try {
      await abortRealWorldTestRun(runId);
      await loadRuns();
      setSelectedRun(null);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <RequireRole
      allowedRoles={["admin", "sales", "reviewer"]}
      deniedMessage="Nur Admin-, Sales- und Reviewer-Konten haben Zugriff auf Real-World Test Mode."
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Real-World Test Mode</h1>
          <p className="mt-1 text-sm text-slate-600">
            Kontrollierte Testläufe mit echten Leads und echten Websites, optional mit
            echten LLM-Ausgaben — ohne automatischen E-Mail-Versand oder automatische
            Kontaktaufnahme.
          </p>
        </div>

        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <p className="font-medium">Wichtiger Hinweis</p>
          <ul className="mt-1 list-inside list-disc space-y-0.5">
            <li>Es gibt keinen Versand-Button und keinen Versand-Endpoint.</li>
            <li>
              &quot;Completed&quot; bedeutet nicht, dass etwas versendet wurde — Human
              Review bleibt erforderlich.
            </li>
            <li>Do-not-contact wird bei jedem Testlauf geprüft, unabhängig vom Modus.</li>
            <li>
              Safe/Mock ist der Standard-Modus; echte LLM-Ausgaben erfordern eine
              explizite Systemkonfiguration (<code>LLM_ENABLE_REAL_CALLS=true</code>).
            </li>
          </ul>
        </div>

        {actionError ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {actionError}
          </div>
        ) : null}

        {canRun ? (
          <Card title="Neuen Test Run starten">
            <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleCreate}>
              <Input
                label="Name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
              <Select
                label="Modus"
                value={form.mode}
                options={MODE_OPTIONS}
                onChange={(e) =>
                  setForm({ ...form, mode: e.target.value as RealWorldTestRunMode })
                }
              />
              <Select
                label="Lead Candidate (optional)"
                value={form.lead_candidate_id}
                options={[
                  { value: "", label: "— keiner —" },
                  ...leadCandidates
                    .filter((c): c is LeadCandidate & { id: string } => c.id !== null)
                    .map((c) => ({
                      value: c.id,
                      label: c.company_name ?? c.id,
                    })),
                ]}
                onChange={(e) => setForm({ ...form, lead_candidate_id: e.target.value })}
              />
              <Select
                label="CRM Lead (optional)"
                value={form.lead_id}
                options={[
                  { value: "", label: "— keiner —" },
                  ...crmLeads.map((l) => ({ value: l.id, label: l.id })),
                ]}
                onChange={(e) => setForm({ ...form, lead_id: e.target.value })}
              />
              <Select
                label="ICP Profile (optional)"
                value={form.icp_profile_id}
                options={[
                  { value: "", label: "— keins —" },
                  ...icpProfiles.map((p) => ({ value: p.id, label: p.name })),
                ]}
                onChange={(e) => setForm({ ...form, icp_profile_id: e.target.value })}
              />
              <Select
                label="Offer Profile (optional)"
                value={form.offer_profile_id}
                options={[
                  { value: "", label: "— keins —" },
                  ...offerProfiles.map((p) => ({ value: p.id, label: p.name })),
                ]}
                onChange={(e) => setForm({ ...form, offer_profile_id: e.target.value })}
              />
              <Input
                label="Firmenname (Fallback/Override)"
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
              />
              <Input
                label="Website-URL (Fallback/Override)"
                value={form.website_url}
                onChange={(e) => setForm({ ...form, website_url: e.target.value })}
              />
              <Input
                label="Branche (Fallback/Override)"
                value={form.industry}
                onChange={(e) => setForm({ ...form, industry: e.target.value })}
              />
              <Input
                label="Angebot / Produkt (Fallback, falls kein Offer Profile)"
                value={form.product_or_service_offered}
                onChange={(e) =>
                  setForm({ ...form, product_or_service_offered: e.target.value })
                }
              />
              <div className="sm:col-span-2">
                <Textarea
                  label="Notizen"
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                />
              </div>
              <div className="sm:col-span-2">
                <Button type="submit" loading={creating}>
                  Test Run starten
                </Button>
              </div>
            </form>
          </Card>
        ) : null}

        {!canView ? (
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            Test Runs ansehen ist Admin-, Sales- und Reviewer-Konten vorbehalten.
          </div>
        ) : loading ? (
          <p className="text-sm text-slate-500">Wird geladen…</p>
        ) : error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        ) : (
          <Card title="Vergangene Test Runs">
            <div className="space-y-2">
              {runs.length === 0 ? (
                <p className="text-sm text-slate-500">Noch keine Test Runs.</p>
              ) : null}
              {runs.map((run) => (
                <div key={run.id} className="rounded-lg border border-slate-200 px-3 py-2">
                  <button
                    type="button"
                    className="flex w-full flex-wrap items-center justify-between gap-2 text-left"
                    onClick={() => setSelectedRun(selectedRun?.id === run.id ? null : run)}
                  >
                    <div>
                      <span className="text-sm font-semibold text-slate-900">
                        {run.name}
                      </span>
                      <span className="ml-2 text-xs text-slate-500">{run.mode}</span>
                    </div>
                    <Badge tone={STATUS_TONE[run.status] ?? "neutral"}>{run.status}</Badge>
                  </button>

                  {selectedRun?.id === run.id ? (
                    <div className="mt-3 space-y-3 border-t border-slate-100 pt-3 text-sm">
                      <p className="text-xs text-slate-500">
                        Erstellt: {new Date(run.created_at).toLocaleString("de-DE")}
                        {run.aborted_at
                          ? ` · Abgebrochen: ${new Date(run.aborted_at).toLocaleString("de-DE")}`
                          : ""}
                      </p>
                      {run.workflow_run_id ? (
                        <p className="text-xs text-slate-600">
                          Workflow Run:{" "}
                          <a
                            className="text-brand-700 underline hover:no-underline"
                            href={`/workflows/history/${run.workflow_run_id}`}
                          >
                            {run.workflow_run_id}
                          </a>
                        </p>
                      ) : null}
                      {run.workflow_run_id ? (
                        <QualityScoreBadge
                          entityType="workflow_run"
                          entityId={run.workflow_run_id}
                        />
                      ) : null}
                      {run.warnings.length > 0 ? (
                        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                          <p className="font-semibold">Warnungen</p>
                          {run.warnings.map((w) => (
                            <p key={w}>• {w}</p>
                          ))}
                        </div>
                      ) : null}
                      {run.errors.length > 0 ? (
                        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                          <p className="font-semibold">Fehler</p>
                          {run.errors.map((err) => (
                            <p key={err}>• {err}</p>
                          ))}
                        </div>
                      ) : null}
                      <div>
                        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                          Input Snapshot
                        </p>
                        <JsonViewer data={run.input_snapshot} />
                      </div>
                      <div>
                        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
                          Result Snapshot
                        </p>
                        <JsonViewer data={run.result_snapshot} />
                      </div>
                      <p className="text-xs text-slate-500">
                        Audit-Hinweis: jede Erstellung, jeder Block und jeder Abbruch
                        dieses Runs wird im Audit Log erfasst (siehe /audit-logs).
                      </p>
                      {canAbort &&
                      !["completed", "blocked", "failed", "aborted"].includes(
                        run.status
                      ) ? (
                        <Button
                          variant="ghost"
                          loading={busyId === run.id}
                          onClick={() => handleAbort(run.id)}
                        >
                          Abbrechen
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </RequireRole>
  );
}
