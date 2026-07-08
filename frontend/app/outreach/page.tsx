"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

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
  archiveOutreachCampaign,
  buildOutreachQueue,
  createOutreachCampaign,
  getICPProfiles,
  getOfferProfiles,
  getOutreachCampaigns,
  getOutreachDashboard,
  getOutreachQueue,
  getOutreachQueueStatus,
  prepareOutreachBatch,
  prepareQueueItemWorkflow,
  updateOutreachCampaignStatus,
  updateOutreachQueueItemStatus,
} from "@/lib/api";
import {
  canManageOutreachQueue,
  canReviewOutreachQueueItem,
  canRunOutreachBatchPreparation,
} from "@/lib/roles";
import type {
  ICPProfile,
  OfferProfile,
  OutreachCampaign,
  OutreachCampaignStatus,
  OutreachQueueDashboardResponse,
  OutreachQueueItem,
  OutreachQueueStatusInfo,
} from "@/lib/types";

const QUEUE_STATUS_TONE: Record<string, "positive" | "info" | "warning" | "negative" | "neutral"> = {
  queued: "info",
  blocked: "negative",
  needs_review: "warning",
  ready_for_workflow: "info",
  workflow_prepared: "info",
  draft_created: "info",
  review_pending: "warning",
  approved: "positive",
  rejected: "negative",
  external_draft_created: "positive",
  replied: "positive",
  archived: "neutral",
};

const CAMPAIGN_STATUS_OPTIONS: { value: OutreachCampaignStatus; label: string }[] = [
  { value: "draft", label: "Draft" },
  { value: "ready", label: "Ready" },
  { value: "active", label: "Active" },
  { value: "paused", label: "Paused" },
  { value: "completed", label: "Completed" },
  { value: "archived", label: "Archived" },
];

function idsFromText(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((id) => id.trim())
    .filter(Boolean);
}

export default function OutreachPage() {
  return (
    <Suspense fallback={null}>
      <OutreachPageContent />
    </Suspense>
  );
}

function OutreachPageContent() {
  const { currentUser } = useAuth();
  const searchParams = useSearchParams();
  const prefillResultId = searchParams.get("qualification_result_id");
  const canManage = canManageOutreachQueue(currentUser);
  const canReview = canReviewOutreachQueueItem(currentUser);
  const canBatch = canRunOutreachBatchPreparation(currentUser);

  const [status, setStatus] = useState<OutreachQueueStatusInfo | null>(null);
  const [dashboard, setDashboard] = useState<OutreachQueueDashboardResponse | null>(null);
  const [campaigns, setCampaigns] = useState<OutreachCampaign[]>([]);
  const [icpProfiles, setIcpProfiles] = useState<ICPProfile[]>([]);
  const [offerProfiles, setOfferProfiles] = useState<OfferProfile[]>([]);
  const [queueItems, setQueueItems] = useState<OutreachQueueItem[]>([]);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string>("");
  const [queueStatusFilter, setQueueStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [campaignForm, setCampaignForm] = useState({
    name: "",
    description: "",
    icp_profile_id: "",
    offer_profile_id: "",
    target_language: "",
    tone: "",
    min_qualification_score: "",
    max_queue_items: "",
  });
  const [creatingCampaign, setCreatingCampaign] = useState(false);
  const [campaignError, setCampaignError] = useState<string | null>(null);

  const [buildForm, setBuildForm] = useState({
    ids_text: "",
    min_score: "",
    max_items: "",
    dry_run: false,
  });
  const [building, setBuilding] = useState(false);
  const [buildError, setBuildError] = useState<string | null>(null);
  const [buildNote, setBuildNote] = useState<string | null>(null);

  const [batchForm, setBatchForm] = useState({ ids_text: "", max_items: "" });
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchNote, setBatchNote] = useState<string | null>(null);

  const [itemActionError, setItemActionError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusResponse, dashboardResponse, campaignsResponse, icpResponse, offerResponse] =
        await Promise.all([
          getOutreachQueueStatus(),
          getOutreachDashboard(),
          getOutreachCampaigns(),
          getICPProfiles(true),
          getOfferProfiles(true),
        ]);
      setStatus(statusResponse);
      setDashboard(dashboardResponse);
      setCampaigns(campaignsResponse.items);
      setIcpProfiles(icpResponse.items);
      setOfferProfiles(offerResponse.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadQueue = useCallback(async () => {
    try {
      const response = await getOutreachQueue({
        campaignId: selectedCampaignId || undefined,
        queueStatus: queueStatusFilter || undefined,
      });
      setQueueItems(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }, [selectedCampaignId, queueStatusFilter]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (prefillResultId) {
      setBuildForm((prev) => ({ ...prev, ids_text: prefillResultId }));
    }
  }, [prefillResultId]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  async function handleCreateCampaign(event: React.FormEvent) {
    event.preventDefault();
    setCreatingCampaign(true);
    setCampaignError(null);
    try {
      const created = await createOutreachCampaign({
        name: campaignForm.name,
        description: campaignForm.description || null,
        icp_profile_id: campaignForm.icp_profile_id || null,
        offer_profile_id: campaignForm.offer_profile_id || null,
        target_language: campaignForm.target_language || null,
        tone: campaignForm.tone || null,
        min_qualification_score: campaignForm.min_qualification_score
          ? Number(campaignForm.min_qualification_score)
          : null,
        max_queue_items: campaignForm.max_queue_items
          ? Number(campaignForm.max_queue_items)
          : null,
      });
      setCampaignForm({
        name: "",
        description: "",
        icp_profile_id: "",
        offer_profile_id: "",
        target_language: "",
        tone: "",
        min_qualification_score: "",
        max_queue_items: "",
      });
      setSelectedCampaignId(created.id);
      await loadAll();
    } catch (err) {
      setCampaignError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setCreatingCampaign(false);
    }
  }

  async function handleSetCampaignStatus(campaignId: string, next: OutreachCampaignStatus) {
    setCampaignError(null);
    try {
      await updateOutreachCampaignStatus(campaignId, { status: next });
      await loadAll();
    } catch (err) {
      setCampaignError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  async function handleArchiveCampaign(campaignId: string) {
    setCampaignError(null);
    try {
      await archiveOutreachCampaign(campaignId);
      await loadAll();
    } catch (err) {
      setCampaignError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  async function handleBuildQueue(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedCampaignId) {
      setBuildError("Bitte zuerst eine Campaign auswählen.");
      return;
    }
    setBuilding(true);
    setBuildError(null);
    setBuildNote(null);
    const ids = idsFromText(buildForm.ids_text);
    try {
      const result = await buildOutreachQueue(selectedCampaignId, {
        qualification_result_ids: ids,
        min_score: buildForm.min_score ? Number(buildForm.min_score) : null,
        max_items: buildForm.max_items ? Number(buildForm.max_items) : null,
        dry_run: buildForm.dry_run,
      });
      setBuildNote(
        `${result.dry_run ? "(Dry Run) " : ""}${result.items.length} Items, ` +
          `${result.skipped_count} übersprungen, ${result.blocked_count} blocked.`
      );
      await loadAll();
      await loadQueue();
    } catch (err) {
      setBuildError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBuilding(false);
    }
  }

  async function handlePrepareBatch(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedCampaignId) {
      setBatchError("Bitte zuerst eine Campaign auswählen.");
      return;
    }
    setBatchRunning(true);
    setBatchError(null);
    setBatchNote(null);
    const ids = idsFromText(batchForm.ids_text);
    try {
      const result = await prepareOutreachBatch(selectedCampaignId, {
        queue_item_ids: ids,
        max_items: batchForm.max_items ? Number(batchForm.max_items) : null,
      });
      setBatchNote(
        `Prepared: ${result.prepared_count} · Skipped: ${result.skipped_count} · ` +
          `Blocked: ${result.blocked_count} · Failed: ${result.failed_count}`
      );
      await loadQueue();
    } catch (err) {
      setBatchError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBatchRunning(false);
    }
  }

  async function handlePrepareItem(itemId: string) {
    setItemActionError(null);
    try {
      await prepareQueueItemWorkflow(itemId, {});
      await loadQueue();
    } catch (err) {
      setItemActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  async function handleItemStatus(itemId: string, queueStatus: string) {
    setItemActionError(null);
    try {
      await updateOutreachQueueItemStatus(itemId, { queue_status: queueStatus as never });
      await loadQueue();
    } catch (err) {
      setItemActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Outreach Queue</h1>
          <p className="mt-1 text-sm text-slate-600">
            Sammelt bereits qualifizierte Leads in priorisierten Campaign-Queues für
            die Übergabe an den Sales Workflow.
          </p>
        </div>

        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <ul className="list-inside list-disc space-y-1">
            <li>Outreach Queue organisiert Leads, sendet aber keine E-Mails.</li>
            <li>Drafts werden nur vorbereitet.</li>
            <li>Human Review bleibt Pflicht.</li>
            <li>Do-not-contact blockiert immer.</li>
            <li>Approved bedeutet nicht Versand.</li>
            <li>Externe Drafts werden nicht automatisch erstellt.</li>
            <li>Es gibt keinen Send Button.</li>
            <li>Mock Provider bleibt Standard.</li>
          </ul>
        </div>

        {status ? (
          <Card title="Status">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={status.enabled ? "positive" : "neutral"}>
                {status.enabled ? "aktiv" : "deaktiviert"}
              </Badge>
              <Badge tone={status.auto_create_external_drafts ? "warning" : "positive"}>
                {status.auto_create_external_drafts
                  ? "Auto External Drafts aktiv"
                  : "Keine automatischen externen Drafts"}
              </Badge>
              <Badge tone="neutral">Default Min Score: {status.default_min_score}</Badge>
              <Badge tone="neutral">Max Batch: {status.max_batch_size}</Badge>
            </div>
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
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
              <div>
                <p className="text-xs text-slate-500">Queued</p>
                <p className="text-lg font-semibold text-slate-900">{dashboard.total_queued}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Ready for Workflow</p>
                <p className="text-lg font-semibold text-slate-900">
                  {dashboard.total_ready_for_workflow}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Workflow Prepared</p>
                <p className="text-lg font-semibold text-slate-900">
                  {dashboard.total_workflow_prepared}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Draft Created</p>
                <p className="text-lg font-semibold text-slate-900">
                  {dashboard.total_draft_created}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Review Pending</p>
                <p className="text-lg font-semibold text-slate-900">
                  {dashboard.total_review_pending}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Approved</p>
                <p className="text-lg font-semibold text-slate-900">{dashboard.total_approved}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Rejected</p>
                <p className="text-lg font-semibold text-slate-900">{dashboard.total_rejected}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Blocked</p>
                <p className="text-lg font-semibold text-slate-900">{dashboard.total_blocked}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Needs Review</p>
                <p className="text-lg font-semibold text-slate-900">
                  {dashboard.total_needs_review}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Archived</p>
                <p className="text-lg font-semibold text-slate-900">{dashboard.total_archived}</p>
              </div>
            </div>
          </Card>
        ) : null}

        {canManage ? (
          <Card title="Neue Campaign erstellen">
            <form className="space-y-4" onSubmit={handleCreateCampaign}>
              <Input
                label="Name"
                value={campaignForm.name}
                required
                onChange={(e) => setCampaignForm({ ...campaignForm, name: e.target.value })}
              />
              <Textarea
                label="Beschreibung (optional)"
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
                  label="Zielsprache (optional)"
                  value={campaignForm.target_language}
                  onChange={(e) =>
                    setCampaignForm({ ...campaignForm, target_language: e.target.value })
                  }
                />
                <Input
                  label="Tone (optional)"
                  value={campaignForm.tone}
                  onChange={(e) => setCampaignForm({ ...campaignForm, tone: e.target.value })}
                />
                <Input
                  label="Min Qualification Score (optional)"
                  type="number"
                  min={0}
                  max={100}
                  value={campaignForm.min_qualification_score}
                  onChange={(e) =>
                    setCampaignForm({
                      ...campaignForm,
                      min_qualification_score: e.target.value,
                    })
                  }
                />
                <Input
                  label="Max Queue Items (optional)"
                  type="number"
                  min={1}
                  max={500}
                  value={campaignForm.max_queue_items}
                  onChange={(e) =>
                    setCampaignForm({ ...campaignForm, max_queue_items: e.target.value })
                  }
                />
              </div>
              <Button type="submit" loading={creatingCampaign}>
                Campaign erstellen
              </Button>
              {campaignError ? <p className="text-sm text-rose-600">{campaignError}</p> : null}
            </form>
          </Card>
        ) : null}

        <Card title="Campaigns">
          {campaigns.length > 0 ? (
            <div className="space-y-2">
              {campaigns.map((campaign) => (
                <div
                  key={campaign.id}
                  className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 ${
                    selectedCampaignId === campaign.id
                      ? "border-brand-400 bg-brand-50"
                      : "border-slate-200"
                  }`}
                >
                  <button
                    type="button"
                    className="text-left text-sm font-medium text-slate-900"
                    onClick={() => setSelectedCampaignId(campaign.id)}
                  >
                    {campaign.name}
                  </button>
                  <div className="flex flex-wrap items-center gap-1">
                    <Badge tone="neutral">{campaign.status}</Badge>
                    {canManage ? (
                      <>
                        <Select
                          label=""
                          value=""
                          options={[
                            { value: "", label: "Status ändern…" },
                            ...CAMPAIGN_STATUS_OPTIONS.filter(
                              (o) => o.value !== campaign.status
                            ),
                          ]}
                          onChange={(e) => {
                            if (e.target.value) {
                              handleSetCampaignStatus(
                                campaign.id,
                                e.target.value as OutreachCampaignStatus
                              );
                            }
                          }}
                        />
                        <Button
                          variant="ghost"
                          onClick={() => handleArchiveCampaign(campaign.id)}
                        >
                          Archivieren
                        </Button>
                      </>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Noch keine Campaigns.</p>
          )}
        </Card>

        {canManage && selectedCampaignId ? (
          <Card title="Queue bauen">
            <form className="space-y-4" onSubmit={handleBuildQueue}>
              <Textarea
                label="Qualification Result IDs (kommagetrennt oder eine pro Zeile)"
                value={buildForm.ids_text}
                onChange={(e) => setBuildForm({ ...buildForm, ids_text: e.target.value })}
                hint="Leer lassen, um automatisch die besten offenen qualified/priority Ergebnisse zu verwenden."
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Min Score (optional)"
                  type="number"
                  min={0}
                  max={100}
                  value={buildForm.min_score}
                  onChange={(e) => setBuildForm({ ...buildForm, min_score: e.target.value })}
                />
                <Input
                  label="Max Items (optional)"
                  type="number"
                  min={1}
                  max={500}
                  value={buildForm.max_items}
                  onChange={(e) => setBuildForm({ ...buildForm, max_items: e.target.value })}
                />
                <label className="flex items-center gap-2 pt-6 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    checked={buildForm.dry_run}
                    onChange={(e) => setBuildForm({ ...buildForm, dry_run: e.target.checked })}
                  />
                  Dry Run (keine dauerhaften Queue Items)
                </label>
              </div>
              <Button type="submit" loading={building}>
                Queue bauen
              </Button>
              {buildError ? <p className="text-sm text-rose-600">{buildError}</p> : null}
              {buildNote ? <p className="text-sm text-slate-600">{buildNote}</p> : null}
            </form>
          </Card>
        ) : null}

        {canBatch && selectedCampaignId ? (
          <Card title="Batch Preparation">
            <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
              Diese Aktion bereitet interne Workflows/Drafts vor, sendet aber keine E-Mails.
            </div>
            <form className="space-y-4" onSubmit={handlePrepareBatch}>
              <Textarea
                label="Queue Item IDs (optional, kommagetrennt oder eine pro Zeile)"
                value={batchForm.ids_text}
                onChange={(e) => setBatchForm({ ...batchForm, ids_text: e.target.value })}
                hint="Leer lassen, um automatisch die nächsten 'ready_for_workflow'/'queued' Items zu verwenden."
              />
              <Input
                label="Max Items (optional)"
                type="number"
                min={1}
                max={500}
                value={batchForm.max_items}
                onChange={(e) => setBatchForm({ ...batchForm, max_items: e.target.value })}
              />
              <Button type="submit" loading={batchRunning}>
                Workflows intern vorbereiten
              </Button>
              {batchError ? <p className="text-sm text-rose-600">{batchError}</p> : null}
              {batchNote ? <p className="text-sm text-slate-600">{batchNote}</p> : null}
            </form>
          </Card>
        ) : null}

        <Card title="Queue Items">
          <div className="mb-4 grid gap-4 sm:grid-cols-2">
            <Select
              label="Campaign Filter"
              value={selectedCampaignId}
              options={[
                { value: "", label: "Alle Campaigns" },
                ...campaigns.map((c) => ({ value: c.id, label: c.name })),
              ]}
              onChange={(e) => setSelectedCampaignId(e.target.value)}
            />
            <Select
              label="Status Filter"
              value={queueStatusFilter}
              options={[
                { value: "", label: "Alle Status" },
                ...Object.keys(QUEUE_STATUS_TONE).map((s) => ({ value: s, label: s })),
              ]}
              onChange={(e) => setQueueStatusFilter(e.target.value)}
            />
          </div>

          {itemActionError ? <p className="mb-2 text-sm text-rose-600">{itemActionError}</p> : null}

          {loading ? (
            <p className="text-sm text-slate-500">Wird geladen…</p>
          ) : error ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </div>
          ) : queueItems.length > 0 ? (
            <div className="space-y-3">
              {queueItems.map((item) => (
                <div
                  key={item.id ?? `${item.campaign_id}-${item.lead_id}-${item.lead_candidate_id}`}
                  className="rounded-lg border border-slate-200 bg-white px-4 py-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {item.recommended_outreach_angle ?? "Queue Item"}
                      </p>
                      <p className="text-xs text-slate-600">
                        Rank: {item.priority_rank ?? "—"} · Score: {item.qualification_score} ·{" "}
                        {item.qualification_level}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      <Badge tone={QUEUE_STATUS_TONE[item.queue_status] ?? "neutral"}>
                        {item.queue_status}
                      </Badge>
                      {item.compliance_status === "blocked" ? (
                        <Badge tone="negative">do-not-contact</Badge>
                      ) : null}
                      {item.duplicate_status === "duplicate" ? (
                        <Badge tone="neutral">duplicate</Badge>
                      ) : null}
                    </div>
                  </div>

                  {item.personalization_notes ? (
                    <p className="mt-2 text-xs text-slate-600">{item.personalization_notes}</p>
                  ) : null}

                  {item.last_error ? (
                    <p className="mt-2 text-xs text-rose-600">{item.last_error}</p>
                  ) : null}

                  <div className="mt-2 flex flex-wrap gap-3 text-xs">
                    {item.lead_id ? (
                      <a href="/crm" className="underline hover:no-underline">
                        Lead öffnen
                      </a>
                    ) : null}
                    {item.company_id ? (
                      <a href="/crm" className="underline hover:no-underline">
                        Company öffnen
                      </a>
                    ) : null}
                    {item.lead_candidate_id ? (
                      <a href="/lead-sourcing" className="underline hover:no-underline">
                        Candidate öffnen
                      </a>
                    ) : null}
                    {item.email_draft_id ? (
                      <a href="/reviews" className="underline hover:no-underline">
                        Draft/Review öffnen
                      </a>
                    ) : null}
                    <a href="/workflows/sales" className="underline hover:no-underline">
                      Sales Workflow öffnen
                    </a>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {canManage &&
                    item.id &&
                    ["queued", "ready_for_workflow", "needs_review"].includes(
                      item.queue_status
                    ) ? (
                      <Button onClick={() => handlePrepareItem(item.id as string)}>
                        Für Workflow vorbereiten
                      </Button>
                    ) : null}
                    {canReview && item.id && item.queue_status === "review_pending" ? (
                      <>
                        <Button
                          variant="secondary"
                          onClick={() => handleItemStatus(item.id as string, "approved")}
                        >
                          Als priority bestätigen (approved)
                        </Button>
                        <Button
                          variant="ghost"
                          onClick={() => handleItemStatus(item.id as string, "rejected")}
                        >
                          Als disqualified markieren (rejected)
                        </Button>
                      </>
                    ) : null}
                    {canReview &&
                    item.id &&
                    !["archived", "rejected", "external_draft_created", "replied"].includes(
                      item.queue_status
                    ) ? (
                      <Button
                        variant="ghost"
                        onClick={() => handleItemStatus(item.id as string, "archived")}
                      >
                        Archivieren
                      </Button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Noch keine Queue Items.</p>
          )}
        </Card>
      </div>
    </RequireAuth>
  );
}
