"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { QualityScoreBadge } from "@/components/quality/QualityScoreBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import {
  ApiError,
  approveLeadCandidate,
  archiveLeadSourcingCampaign,
  createLeadSourcingCampaign,
  getICPProfiles,
  getLeadCandidates,
  getLeadSourcingCampaigns,
  getLeadSourcingRuns,
  getLeadSourcingStatus,
  getOfferProfiles,
  importLeadCandidates,
  qualifyLeadCandidate,
  rejectLeadCandidate,
  startLeadSourcingRun,
  updateLeadSourcingCampaign,
} from "@/lib/api";
import {
  canArchiveLeadSourcingCampaign,
  canManageLeadQualification,
  canManageLeadSourcing,
  canReviewLeadCandidate,
} from "@/lib/roles";
import type {
  ICPProfile,
  LeadCandidate,
  LeadQualificationResult,
  LeadSourcingCampaign,
  LeadSourcingProviderStatus,
  LeadSourcingRun,
  OfferProfile,
} from "@/lib/types";

const FIT_LEVEL_TONE: Record<string, "positive" | "info" | "warning" | "negative" | "neutral"> = {
  excellent: "positive",
  good: "positive",
  medium: "info",
  weak: "warning",
  not_fit: "negative",
};

const DNC_TONE: Record<string, "positive" | "negative" | "neutral"> = {
  clear: "positive",
  blocked: "negative",
  unknown: "neutral",
};

const DUPLICATE_TONE: Record<string, "positive" | "warning" | "neutral"> = {
  new: "positive",
  duplicate: "warning",
  unknown: "neutral",
};

const REVIEW_TONE: Record<string, "positive" | "negative" | "warning" | "neutral"> = {
  approved: "positive",
  rejected: "negative",
  pending: "warning",
};

const EMPTY_CAMPAIGN_FORM = {
  name: "",
  description: "",
  icp_profile_id: "",
  offer_profile_id: "",
  target_industry: "",
  target_location: "",
  target_keywords: "",
  excluded_keywords: "",
  max_results: "25",
};

function linesToList(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export default function LeadSourcingPage() {
  const { currentUser } = useAuth();
  const canManage = canManageLeadSourcing(currentUser);
  const canArchive = canArchiveLeadSourcingCampaign(currentUser);
  const canReview = canReviewLeadCandidate(currentUser);
  const canQualify = canManageLeadQualification(currentUser);

  const [status, setStatus] = useState<LeadSourcingProviderStatus | null>(null);
  const [campaigns, setCampaigns] = useState<LeadSourcingCampaign[]>([]);
  const [icpProfiles, setIcpProfiles] = useState<ICPProfile[]>([]);
  const [offerProfiles, setOfferProfiles] = useState<OfferProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [runs, setRuns] = useState<LeadSourcingRun[]>([]);
  const [candidates, setCandidates] = useState<LeadCandidate[]>([]);
  const [candidatesLoading, setCandidatesLoading] = useState(false);

  const [campaignForm, setCampaignForm] = useState(EMPTY_CAMPAIGN_FORM);
  const [editingCampaignId, setEditingCampaignId] = useState<string | null>(null);
  const [savingCampaign, setSavingCampaign] = useState(false);
  const [campaignFormError, setCampaignFormError] = useState<string | null>(null);

  const [runStarting, setRunStarting] = useState<"run" | "dry_run" | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const [importText, setImportText] = useState("");
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importResultNote, setImportResultNote] = useState<string | null>(null);

  const [expandedCandidateId, setExpandedCandidateId] = useState<string | null>(null);
  const [candidateActionError, setCandidateActionError] = useState<string | null>(null);
  const [qualificationResults, setQualificationResults] = useState<
    Record<string, LeadQualificationResult>
  >({});
  const [qualifyingCandidateId, setQualifyingCandidateId] = useState<string | null>(null);
  const [qualifyError, setQualifyError] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusResponse, campaignsResponse, icpResponse, offerResponse] =
        await Promise.all([
          getLeadSourcingStatus(),
          getLeadSourcingCampaigns(),
          getICPProfiles(true),
          getOfferProfiles(true),
        ]);
      setStatus(statusResponse);
      setCampaigns(campaignsResponse.items);
      setIcpProfiles(icpResponse.items);
      setOfferProfiles(offerResponse.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  const loadCampaignDetails = useCallback(async (campaignId: string) => {
    setCandidatesLoading(true);
    try {
      const [runsResponse, candidatesResponse] = await Promise.all([
        getLeadSourcingRuns(campaignId),
        getLeadCandidates({ campaignId }),
      ]);
      setRuns(runsResponse.items);
      setCandidates(candidatesResponse.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setCandidatesLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedCampaignId) {
      loadCampaignDetails(selectedCampaignId);
    } else {
      setRuns([]);
      setCandidates([]);
    }
  }, [selectedCampaignId, loadCampaignDetails]);

  function startEditCampaign(campaign: LeadSourcingCampaign) {
    setEditingCampaignId(campaign.id);
    setCampaignForm({
      name: campaign.name,
      description: campaign.description ?? "",
      icp_profile_id: campaign.icp_profile_id ?? "",
      offer_profile_id: campaign.offer_profile_id ?? "",
      target_industry: campaign.target_industry ?? "",
      target_location: campaign.target_location ?? "",
      target_keywords: campaign.target_keywords.join("\n"),
      excluded_keywords: campaign.excluded_keywords.join("\n"),
      max_results: String(campaign.max_results),
    });
  }

  function resetCampaignForm() {
    setEditingCampaignId(null);
    setCampaignForm(EMPTY_CAMPAIGN_FORM);
    setCampaignFormError(null);
  }

  async function handleCampaignSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSavingCampaign(true);
    setCampaignFormError(null);
    const payload = {
      name: campaignForm.name.trim(),
      description: campaignForm.description.trim() || null,
      icp_profile_id: campaignForm.icp_profile_id || null,
      offer_profile_id: campaignForm.offer_profile_id || null,
      target_industry: campaignForm.target_industry.trim() || null,
      target_location: campaignForm.target_location.trim() || null,
      target_keywords: linesToList(campaignForm.target_keywords),
      excluded_keywords: linesToList(campaignForm.excluded_keywords),
      max_results: Number(campaignForm.max_results) || 25,
    };
    try {
      if (editingCampaignId) {
        await updateLeadSourcingCampaign(editingCampaignId, payload);
      } else {
        await createLeadSourcingCampaign(payload);
      }
      resetCampaignForm();
      await loadOverview();
    } catch (err) {
      setCampaignFormError(
        err instanceof ApiError ? err.message : "Unerwarteter Fehler."
      );
    } finally {
      setSavingCampaign(false);
    }
  }

  async function handleArchiveCampaign(campaignId: string) {
    try {
      await archiveLeadSourcingCampaign(campaignId);
      await loadOverview();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  async function handleStartRun(dryRun: boolean) {
    if (!selectedCampaignId) return;
    setRunStarting(dryRun ? "dry_run" : "run");
    setRunError(null);
    try {
      const result = await startLeadSourcingRun(selectedCampaignId, {
        campaign_id: selectedCampaignId,
        dry_run: dryRun,
      });
      if (dryRun) {
        setCandidates(result.candidates);
      } else {
        await loadCampaignDetails(selectedCampaignId);
      }
      await loadOverview();
    } catch (err) {
      setRunError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setRunStarting(null);
    }
  }

  async function handleImport(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedCampaignId) return;
    setImporting(true);
    setImportError(null);
    setImportResultNote(null);
    try {
      const result = await importLeadCandidates({
        campaign_id: selectedCampaignId,
        raw_text: importText,
      });
      setImportText("");
      setImportResultNote(
        `${result.total_imported} Kandidat(en) importiert, ${result.total_duplicates} Duplikat(e), ${result.total_blocked_by_do_not_contact} durch Do-not-contact blockiert.`
      );
      await loadCampaignDetails(selectedCampaignId);
    } catch (err) {
      setImportError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setImporting(false);
    }
  }

  async function handleApprove(candidateId: string) {
    setCandidateActionError(null);
    try {
      await approveLeadCandidate(candidateId);
      if (selectedCampaignId) await loadCampaignDetails(selectedCampaignId);
    } catch (err) {
      setCandidateActionError(
        err instanceof ApiError ? err.message : "Unerwarteter Fehler."
      );
    }
  }

  async function handleReject(candidateId: string) {
    setCandidateActionError(null);
    try {
      await rejectLeadCandidate(candidateId);
      if (selectedCampaignId) await loadCampaignDetails(selectedCampaignId);
    } catch (err) {
      setCandidateActionError(
        err instanceof ApiError ? err.message : "Unerwarteter Fehler."
      );
    }
  }

  async function handleQualify(candidateId: string) {
    setQualifyingCandidateId(candidateId);
    setQualifyError(null);
    try {
      const result = await qualifyLeadCandidate(candidateId);
      setQualificationResults((prev) => ({ ...prev, [candidateId]: result }));
    } catch (err) {
      setQualifyError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setQualifyingCandidateId(null);
    }
  }

  const duplicateCount = candidates.filter((c) => c.duplicate_status === "duplicate").length;
  const blockedCount = candidates.filter((c) => c.do_not_contact_status === "blocked").length;
  const scored = candidates.filter((c) => c.icp_fit_score != null);
  const avgFitScore =
    scored.length > 0
      ? Math.round(
          scored.reduce((sum, c) => sum + (c.icp_fit_score ?? 0), 0) / scored.length
        )
      : null;

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Lead Sourcing</h1>
          <p className="mt-1 text-sm text-slate-600">
            Findet und bewertet potenzielle Kunden anhand von ICP und Offer —
            zur Vorbereitung für den Sales Workflow.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Nächster Schritt nach dem Sourcing:{" "}
            <a href="/lead-qualification" className="underline hover:no-underline">
              Lead Qualification
            </a>
            .
          </p>
        </div>

        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <ul className="list-inside list-disc space-y-1">
            <li>Lead Sourcing findet und bewertet potenzielle Kunden.</li>
            <li>Es werden keine E-Mails automatisch gesendet.</li>
            <li>Es gibt keinen Send Button.</li>
            <li>Kandidaten werden vor CRM-Übernahme geprüft.</li>
            <li>Do-not-contact blockiert Kandidaten.</li>
            <li>LinkedIn Scraping ist nicht erlaubt.</li>
            <li>Persönliche E-Mails werden nicht erraten.</li>
            <li>Mock Provider ist Standard.</li>
          </ul>
        </div>

        {status ? (
          <Card title="Provider Status">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={status.provider === "mock" ? "info" : "positive"}>
                Provider: {status.provider}
              </Badge>
              <Badge tone={status.real_search_enabled ? "warning" : "positive"}>
                {status.real_search_enabled ? "Echte Suche aktiv" : "Safe Mode (Mock)"}
              </Badge>
              <Badge tone="neutral">Status: {status.status}</Badge>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600 sm:grid-cols-4">
              <p>Max. Ergebnisse/Run: {status.max_results_per_run}</p>
              <p>Max. Website-Seiten: {status.max_website_pages_per_company}</p>
              <p>
                Öffentliche E-Mail-Extraktion:{" "}
                {status.allow_public_website_email_extraction ? "an" : "aus"}
              </p>
              <p>Persönliche E-Mails: {status.allow_personal_emails ? "erlaubt" : "gesperrt"}</p>
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

        {canManage ? (
          <Card title={editingCampaignId ? "Campaign bearbeiten" : "Neue Campaign erstellen"}>
            <form className="space-y-4" onSubmit={handleCampaignSubmit}>
              <Input
                label="Name *"
                required
                value={campaignForm.name}
                onChange={(e) => setCampaignForm({ ...campaignForm, name: e.target.value })}
              />
              <Textarea
                label="Beschreibung"
                value={campaignForm.description}
                onChange={(e) =>
                  setCampaignForm({ ...campaignForm, description: e.target.value })
                }
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Select
                  label="ICP Profil (optional)"
                  value={campaignForm.icp_profile_id}
                  options={[
                    { value: "", label: "Keins" },
                    ...icpProfiles.map((p) => ({ value: p.id, label: p.name })),
                  ]}
                  onChange={(e) =>
                    setCampaignForm({ ...campaignForm, icp_profile_id: e.target.value })
                  }
                />
                <Select
                  label="Offer Profil (optional)"
                  value={campaignForm.offer_profile_id}
                  options={[
                    { value: "", label: "Keins" },
                    ...offerProfiles.map((p) => ({ value: p.id, label: p.name })),
                  ]}
                  onChange={(e) =>
                    setCampaignForm({ ...campaignForm, offer_profile_id: e.target.value })
                  }
                />
                <Input
                  label="Zielbranche"
                  value={campaignForm.target_industry}
                  onChange={(e) =>
                    setCampaignForm({ ...campaignForm, target_industry: e.target.value })
                  }
                />
                <Input
                  label="Zielregion"
                  value={campaignForm.target_location}
                  onChange={(e) =>
                    setCampaignForm({ ...campaignForm, target_location: e.target.value })
                  }
                />
                <Textarea
                  label="Zielkeywords (eines pro Zeile)"
                  value={campaignForm.target_keywords}
                  onChange={(e) =>
                    setCampaignForm({ ...campaignForm, target_keywords: e.target.value })
                  }
                />
                <Textarea
                  label="Ausgeschlossene Keywords (eines pro Zeile)"
                  value={campaignForm.excluded_keywords}
                  onChange={(e) =>
                    setCampaignForm({ ...campaignForm, excluded_keywords: e.target.value })
                  }
                />
              </div>
              <Input
                label="Max. Ergebnisse"
                type="number"
                min={1}
                max={200}
                value={campaignForm.max_results}
                onChange={(e) =>
                  setCampaignForm({ ...campaignForm, max_results: e.target.value })
                }
              />
              <div className="flex gap-2">
                <Button type="submit" loading={savingCampaign}>
                  {editingCampaignId ? "Speichern" : "Campaign erstellen"}
                </Button>
                {editingCampaignId ? (
                  <Button type="button" variant="ghost" onClick={resetCampaignForm}>
                    Abbrechen
                  </Button>
                ) : null}
              </div>
              {campaignFormError ? (
                <p className="text-sm text-rose-600">{campaignFormError}</p>
              ) : null}
            </form>
          </Card>
        ) : null}

        <Card title="Campaigns">
          {loading ? (
            <p className="text-sm text-slate-500">Campaigns werden geladen…</p>
          ) : error ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </div>
          ) : campaigns.length > 0 ? (
            <div className="space-y-2">
              {campaigns.map((campaign) => (
                <div
                  key={campaign.id}
                  className={`rounded-lg border px-4 py-3 ${
                    selectedCampaignId === campaign.id
                      ? "border-brand-400 bg-brand-50"
                      : "border-slate-200 bg-white"
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <button
                      type="button"
                      className="text-left"
                      onClick={() => setSelectedCampaignId(campaign.id)}
                    >
                      <p className="text-sm font-semibold text-slate-900">
                        {campaign.name}
                      </p>
                      <p className="text-xs text-slate-600">
                        {campaign.target_industry ?? "Keine Branche"} ·{" "}
                        {campaign.target_location ?? "Keine Region"} · max{" "}
                        {campaign.max_results}
                      </p>
                    </button>
                    <Badge tone="neutral">{campaign.status}</Badge>
                  </div>
                  <div className="mt-2 flex gap-2">
                    <Button variant="ghost" onClick={() => setSelectedCampaignId(campaign.id)}>
                      Auswählen
                    </Button>
                    {canManage ? (
                      <Button variant="ghost" onClick={() => startEditCampaign(campaign)}>
                        Bearbeiten
                      </Button>
                    ) : null}
                    {canArchive && campaign.status !== "archived" ? (
                      <Button variant="ghost" onClick={() => handleArchiveCampaign(campaign.id)}>
                        Archivieren
                      </Button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Noch keine Campaigns vorhanden.</p>
          )}
        </Card>

        {selectedCampaignId ? (
          <>
            <Card title="Dashboard">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div>
                  <p className="text-xs text-slate-500">Kandidaten</p>
                  <p className="text-lg font-semibold text-slate-900">{candidates.length}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Duplikate</p>
                  <p className="text-lg font-semibold text-slate-900">{duplicateCount}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Do-not-contact Blocks</p>
                  <p className="text-lg font-semibold text-slate-900">{blockedCount}</p>
                </div>
                <div>
                  <p className="text-xs text-slate-500">Ø ICP Fit Score</p>
                  <p className="text-lg font-semibold text-slate-900">
                    {avgFitScore ?? "—"}
                  </p>
                </div>
              </div>
            </Card>

            {canManage ? (
              <Card title="Run starten">
                <div className="flex flex-wrap gap-2">
                  <Button loading={runStarting === "run"} onClick={() => handleStartRun(false)}>
                    Run starten
                  </Button>
                  <Button
                    variant="secondary"
                    loading={runStarting === "dry_run"}
                    onClick={() => handleStartRun(true)}
                  >
                    Dry Run starten
                  </Button>
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  Dry Run zeigt Kandidaten nur zur Vorschau — es wird nichts
                  dauerhaft gespeichert.
                </p>
                {runError ? <p className="mt-2 text-sm text-rose-600">{runError}</p> : null}
              </Card>
            ) : null}

            <Card title="Runs">
              {runs.length > 0 ? (
                <div className="space-y-2">
                  {runs.map((run) => (
                    <div
                      key={run.id}
                      className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          tone={
                            run.status === "completed"
                              ? "positive"
                              : run.status === "failed"
                                ? "negative"
                                : "neutral"
                          }
                        >
                          {run.status}
                        </Badge>
                        <span className="text-xs text-slate-600">
                          Provider: {run.provider} · Gefunden:{" "}
                          {run.total_candidates_found} · Gespeichert:{" "}
                          {run.total_candidates_saved} · Duplikate: {run.total_duplicates}{" "}
                          · Do-not-contact: {run.total_blocked_by_do_not_contact}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-slate-500">Noch keine Runs für diese Campaign.</p>
              )}
            </Card>

            {canManage ? (
              <Card title="Manueller Import">
                <form className="space-y-3" onSubmit={handleImport}>
                  <Textarea
                    label="Kandidaten (eine Zeile pro Kandidat)"
                    value={importText}
                    onChange={(e) => setImportText(e.target.value)}
                    hint="Format: company_name, domain, website_url, notes — Felder können leer bleiben, aber company_name oder domain ist erforderlich."
                  />
                  <Button type="submit" loading={importing}>
                    Importieren
                  </Button>
                  {importError ? (
                    <p className="text-sm text-rose-600">{importError}</p>
                  ) : null}
                  {importResultNote ? (
                    <p className="text-sm text-slate-600">{importResultNote}</p>
                  ) : null}
                </form>
              </Card>
            ) : null}

            <Card title="Kandidaten">
              {candidatesLoading ? (
                <p className="text-sm text-slate-500">Kandidaten werden geladen…</p>
              ) : candidates.length > 0 ? (
                <div className="space-y-3">
                  {candidateActionError ? (
                    <p className="text-sm text-rose-600">{candidateActionError}</p>
                  ) : null}
                  {candidates.map((candidate) => {
                    const isExpanded = expandedCandidateId === (candidate.id ?? "");
                    return (
                      <div
                        key={candidate.id ?? candidate.company_name}
                        className="rounded-lg border border-slate-200 bg-white px-4 py-3"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <button
                            type="button"
                            className="text-left"
                            onClick={() =>
                              setExpandedCandidateId(isExpanded ? null : candidate.id ?? "")
                            }
                          >
                            <p className="text-sm font-semibold text-slate-900">
                              {candidate.company_name ?? candidate.company_domain}
                            </p>
                            <p className="text-xs text-slate-600">
                              {candidate.industry ?? "—"} · {candidate.location ?? "—"}
                            </p>
                          </button>
                          <div className="flex flex-wrap gap-1">
                            <Badge
                              tone={
                                candidate.icp_fit_level
                                  ? FIT_LEVEL_TONE[candidate.icp_fit_level]
                                  : "neutral"
                              }
                            >
                              Fit: {candidate.icp_fit_score ?? "—"}
                            </Badge>
                            <Badge tone={DNC_TONE[candidate.do_not_contact_status]}>
                              DNC: {candidate.do_not_contact_status}
                            </Badge>
                            <Badge tone={DUPLICATE_TONE[candidate.duplicate_status]}>
                              {candidate.duplicate_status}
                            </Badge>
                            <Badge tone={REVIEW_TONE[candidate.review_status]}>
                              {candidate.review_status}
                            </Badge>
                            {candidate.id && qualificationResults[candidate.id] ? (
                              <Badge
                                tone={
                                  qualificationResults[candidate.id].qualification_status ===
                                    "priority" ||
                                  qualificationResults[candidate.id].qualification_status ===
                                    "qualified"
                                    ? "positive"
                                    : qualificationResults[candidate.id].qualification_status ===
                                        "needs_review"
                                      ? "warning"
                                      : "negative"
                                }
                              >
                                Qual: {qualificationResults[candidate.id].qualification_score} ·{" "}
                                {qualificationResults[candidate.id].qualification_status}
                              </Badge>
                            ) : null}
                          </div>
                        </div>

                        {isExpanded ? (
                          <div className="mt-3 space-y-2 border-t border-slate-100 pt-3 text-sm">
                            {candidate.id ? (
                              <QualityScoreBadge
                                entityType="lead_candidate"
                                entityId={candidate.id}
                              />
                            ) : null}
                            <dl className="space-y-1 text-xs text-slate-600">
                              <p>Domain: {candidate.company_domain ?? "—"}</p>
                              <p>Website: {candidate.company_website_url ?? "—"}</p>
                              <p>Source: {candidate.source_name ?? candidate.source_type}</p>
                              {candidate.source_url ? (
                                <p>Source URL: {candidate.source_url}</p>
                              ) : null}
                              <p>
                                Public Contact Email:{" "}
                                {candidate.public_contact_email ?? "—"}
                              </p>
                              <p>Contact Page: {candidate.contact_page_url ?? "—"}</p>
                              <p>ICP Fit Level: {candidate.icp_fit_level ?? "—"}</p>
                            </dl>
                            {candidate.matched_signals.length > 0 ? (
                              <div>
                                <p className="text-xs font-semibold text-slate-500">
                                  Matched Signals
                                </p>
                                <ul className="list-inside list-disc text-xs text-slate-700">
                                  {candidate.matched_signals.map((s) => (
                                    <li key={s}>{s}</li>
                                  ))}
                                </ul>
                              </div>
                            ) : null}
                            {candidate.negative_signals.length > 0 ? (
                              <div>
                                <p className="text-xs font-semibold text-rose-500">
                                  Negative Signals
                                </p>
                                <ul className="list-inside list-disc text-xs text-rose-700">
                                  {candidate.negative_signals.map((s) => (
                                    <li key={s}>{s}</li>
                                  ))}
                                </ul>
                              </div>
                            ) : null}
                            {candidate.notes.length > 0 ? (
                              <div>
                                <p className="text-xs font-semibold text-slate-500">Notes</p>
                                <ul className="list-inside list-disc text-xs text-slate-700">
                                  {candidate.notes.map((n) => (
                                    <li key={n}>{n}</li>
                                  ))}
                                </ul>
                              </div>
                            ) : null}
                            {candidate.warnings.length > 0 ? (
                              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                                {candidate.warnings.map((w) => (
                                  <p key={w}>{w}</p>
                                ))}
                              </div>
                            ) : null}
                            {candidate.crm_company_id || candidate.crm_lead_id ? (
                              <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
                                <p>Im CRM übernommen.</p>
                                <div className="mt-1 flex gap-3">
                                  <a href="/crm" className="font-medium underline hover:no-underline">
                                    CRM öffnen
                                  </a>
                                  <a
                                    href="/workflows/sales"
                                    className="font-medium underline hover:no-underline"
                                  >
                                    Sales Workflow manuell starten
                                  </a>
                                </div>
                                <p className="mt-1 text-emerald-700">
                                  Kein automatischer Start — Firmen-/Lead-Daten müssen im
                                  Sales Workflow manuell eingetragen werden.
                                </p>
                              </div>
                            ) : null}
                            {candidate.id && qualificationResults[candidate.id] ? (
                              <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
                                <p className="font-semibold">
                                  Recommended: {qualificationResults[candidate.id].recommended_next_action}
                                </p>
                                {qualificationResults[candidate.id].recommended_outreach_angle ? (
                                  <p>{qualificationResults[candidate.id].recommended_outreach_angle}</p>
                                ) : null}
                                <a
                                  href="/lead-qualification"
                                  className="underline hover:no-underline"
                                >
                                  Qualification Result öffnen
                                </a>
                              </div>
                            ) : null}
                            {qualifyError ? (
                              <p className="text-sm text-rose-600">{qualifyError}</p>
                            ) : null}
                            <div className="flex flex-wrap gap-2 pt-2">
                              {canQualify && candidate.id ? (
                                <Button
                                  variant="secondary"
                                  loading={qualifyingCandidateId === candidate.id}
                                  onClick={() => handleQualify(candidate.id as string)}
                                >
                                  Kandidat qualifizieren
                                </Button>
                              ) : null}
                              {canReview && candidate.review_status === "pending" && candidate.id ? (
                                <>
                                  <Button onClick={() => handleApprove(candidate.id as string)}>
                                    Approve
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    onClick={() => handleReject(candidate.id as string)}
                                  >
                                    Reject
                                  </Button>
                                </>
                              ) : null}
                            </div>
                          </div>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-slate-500">
                  Noch keine Kandidaten für diese Campaign.
                </p>
              )}
            </Card>
          </>
        ) : null}
      </div>
    </RequireAuth>
  );
}
