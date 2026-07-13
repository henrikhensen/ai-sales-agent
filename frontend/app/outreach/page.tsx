"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { QualityScoreBadge } from "@/components/quality/QualityScoreBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import {
  acknowledgeDispatchCompliance,
  ApiError,
  archiveOutreachCampaign,
  buildOutreachQueue,
  checkDispatchReadiness,
  confirmDispatch,
  createDispatch,
  createOutreachCampaign,
  getICPProfiles,
  getOfferProfiles,
  getOutreachCampaigns,
  getOutreachDashboard,
  getOutreachDispatchDashboard,
  getOutreachQueue,
  getOutreachQueueStatus,
  prepareOutreachBatch,
  prepareQueueItemWorkflow,
  updateOutreachCampaignStatus,
  updateOutreachQueueItemStatus,
} from "@/lib/api";
import {
  canManageOutreachDispatch,
  canManageOutreachQueue,
  canReviewOutreachQueueItem,
  canRunOutreachBatchPreparation,
} from "@/lib/roles";
import type {
  DispatchDashboardResponse,
  DispatchReadinessCheckResponse,
  ICPProfile,
  OfferProfile,
  OutreachCampaign,
  OutreachCampaignStatus,
  OutreachDispatch,
  OutreachQueueDashboardResponse,
  OutreachQueueItem,
  OutreachQueueStatusInfo,
} from "@/lib/types";

interface ItemDispatchState {
  readiness?: DispatchReadinessCheckResponse;
  dispatch?: OutreachDispatch;
  loading?: boolean;
  error?: string;
}

const COMPLIANCE_ACK_LABELS: { key: keyof ComplianceAckForm; label: string }[] = [
  {
    key: "contact_permission_confirmed",
    label: "Ich habe geprüft, dass dieser Kontakt kontaktiert werden darf.",
  },
  { key: "do_not_contact_confirmed", label: "Do-not-contact wurde geprüft." },
  { key: "human_review_confirmed", label: "Human Review ist abgeschlossen." },
  {
    key: "draft_or_controlled_send_confirmed",
    label: "Die Nachricht ist ein Draft oder kontrollierter manueller Versand.",
  },
  {
    key: "legal_responsibility_confirmed",
    label: "Ich verstehe, dass rechtliche Verantwortung beim Nutzer liegt.",
  },
];

interface ComplianceAckForm {
  contact_permission_confirmed: boolean;
  do_not_contact_confirmed: boolean;
  human_review_confirmed: boolean;
  draft_or_controlled_send_confirmed: boolean;
  legal_responsibility_confirmed: boolean;
}

const EMPTY_ACK_FORM: ComplianceAckForm = {
  contact_permission_confirmed: false,
  do_not_contact_confirmed: false,
  human_review_confirmed: false,
  draft_or_controlled_send_confirmed: false,
  legal_responsibility_confirmed: false,
};

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
  sent_manually_confirmed: "positive",
  failed: "negative",
  cancelled: "neutral",
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
  const canDispatch = canManageOutreachDispatch(currentUser);

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

  const [dispatchSettings, setDispatchSettings] = useState<DispatchDashboardResponse | null>(
    null
  );
  const [itemDispatch, setItemDispatch] = useState<Record<string, ItemDispatchState>>({});
  const [modalItemId, setModalItemId] = useState<string | null>(null);
  const [ackForm, setAckForm] = useState<ComplianceAckForm>(EMPTY_ACK_FORM);
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [modalBusy, setModalBusy] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        statusResponse,
        dashboardResponse,
        campaignsResponse,
        icpResponse,
        offerResponse,
        dispatchSettingsResponse,
      ] = await Promise.all([
        getOutreachQueueStatus(),
        getOutreachDashboard(),
        getOutreachCampaigns(),
        getICPProfiles(true),
        getOfferProfiles(true),
        getOutreachDispatchDashboard(),
      ]);
      setStatus(statusResponse);
      setDashboard(dashboardResponse);
      setCampaigns(campaignsResponse.items);
      setIcpProfiles(icpResponse.items);
      setOfferProfiles(offerResponse.items);
      setDispatchSettings(dispatchSettingsResponse);
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

  function updateItemDispatch(itemId: string, patch: Partial<ItemDispatchState>) {
    setItemDispatch((prev) => ({ ...prev, [itemId]: { ...prev[itemId], ...patch } }));
  }

  async function handleCheckReadiness(itemId: string) {
    updateItemDispatch(itemId, { loading: true, error: undefined });
    try {
      const readiness = await checkDispatchReadiness(itemId, {});
      updateItemDispatch(itemId, { readiness, loading: false });
    } catch (err) {
      updateItemDispatch(itemId, {
        loading: false,
        error: err instanceof ApiError ? err.message : "Unerwarteter Fehler.",
      });
    }
  }

  async function handlePrepareDispatch(itemId: string) {
    updateItemDispatch(itemId, { loading: true, error: undefined });
    try {
      const result = await createDispatch(itemId, {});
      updateItemDispatch(itemId, {
        dispatch: result.dispatch,
        readiness: result.readiness,
        loading: false,
      });
      setModalItemId(itemId);
      setAckForm(EMPTY_ACK_FORM);
      setConfirmChecked(false);
      setModalError(null);
    } catch (err) {
      updateItemDispatch(itemId, {
        loading: false,
        error: err instanceof ApiError ? err.message : "Unerwarteter Fehler.",
      });
    }
  }

  async function handleModalAcknowledge() {
    if (!modalItemId) return;
    const dispatch = itemDispatch[modalItemId]?.dispatch;
    if (!dispatch) return;
    setModalBusy(true);
    setModalError(null);
    try {
      const result = await acknowledgeDispatchCompliance(dispatch.id, ackForm);
      updateItemDispatch(modalItemId, { dispatch: result.dispatch });
    } catch (err) {
      setModalError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setModalBusy(false);
    }
  }

  async function handleModalConfirm() {
    if (!modalItemId) return;
    const dispatch = itemDispatch[modalItemId]?.dispatch;
    if (!dispatch) return;
    setModalBusy(true);
    setModalError(null);
    try {
      const result = await confirmDispatch(dispatch.id, { confirmed: true });
      updateItemDispatch(modalItemId, { dispatch: result.dispatch });
      await loadQueue();
    } catch (err) {
      setModalError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setModalBusy(false);
    }
  }

  function closeModal() {
    setModalItemId(null);
    setModalError(null);
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

        <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
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
              <div className="mt-3 rounded-lg border border-amber-400/25 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
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
              {campaignError ? <p className="text-sm text-rose-400">{campaignError}</p> : null}
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
              {buildError ? <p className="text-sm text-rose-400">{buildError}</p> : null}
              {buildNote ? <p className="text-sm text-slate-600">{buildNote}</p> : null}
            </form>
          </Card>
        ) : null}

        {canBatch && selectedCampaignId ? (
          <Card title="Batch Preparation">
            <div className="mb-3 rounded-lg border border-amber-400/25 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
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
              {batchError ? <p className="text-sm text-rose-400">{batchError}</p> : null}
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

          {itemActionError ? <p className="mb-2 text-sm text-rose-400">{itemActionError}</p> : null}

          {loading ? (
            <p className="text-sm text-slate-500">Wird geladen…</p>
          ) : error ? (
            <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </div>
          ) : queueItems.length > 0 ? (
            <div className="space-y-3">
              {queueItems.map((item) => (
                <div
                  key={item.id ?? `${item.campaign_id}-${item.lead_id}-${item.lead_candidate_id}`}
                  className="rounded-lg border border-slate-200 bg-surface px-4 py-3"
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

                  {item.id ? (
                    <div className="mt-2">
                      <QualityScoreBadge entityType="outreach_queue_item" entityId={item.id} />
                    </div>
                  ) : null}

                  {item.personalization_notes ? (
                    <p className="mt-2 text-xs text-slate-600">{item.personalization_notes}</p>
                  ) : null}

                  {item.last_error ? (
                    <p className="mt-2 text-xs text-rose-400">{item.last_error}</p>
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

                  {canDispatch &&
                  item.id &&
                  ["approved", "external_draft_created"].includes(item.queue_status) ? (
                    <div className="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                      <p className="text-xs font-semibold uppercase text-slate-500">
                        Controlled Dispatch
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <Button
                          variant="secondary"
                          loading={itemDispatch[item.id]?.loading}
                          onClick={() => handleCheckReadiness(item.id as string)}
                        >
                          Readiness prüfen
                        </Button>
                        <Button
                          loading={itemDispatch[item.id]?.loading}
                          onClick={() => handlePrepareDispatch(item.id as string)}
                        >
                          Externen Draft vorbereiten
                        </Button>
                        {itemDispatch[item.id]?.dispatch ? (
                          <Badge
                            tone={
                              itemDispatch[item.id]?.dispatch?.dispatch_status === "blocked"
                                ? "negative"
                                : "info"
                            }
                          >
                            Dispatch: {itemDispatch[item.id]?.dispatch?.dispatch_status}
                          </Badge>
                        ) : null}
                      </div>
                      {itemDispatch[item.id]?.error ? (
                        <p className="mt-2 text-xs text-rose-400">
                          {itemDispatch[item.id]?.error}
                        </p>
                      ) : null}
                      {itemDispatch[item.id]?.readiness ? (
                        <div className="mt-2 text-xs">
                          <p
                            className={
                              itemDispatch[item.id]?.readiness?.is_ready
                                ? "text-emerald-200"
                                : "text-rose-200"
                            }
                          >
                            {itemDispatch[item.id]?.readiness?.is_ready
                              ? "Bereit für Dispatch."
                              : "Noch nicht bereit."}
                          </p>
                          {itemDispatch[item.id]?.readiness?.blockers.map((b) => (
                            <p key={b} className="text-rose-400">
                              • {b}
                            </p>
                          ))}
                          {itemDispatch[item.id]?.readiness?.warnings.map((w) => (
                            <p key={w} className="text-amber-200">
                              ⚠ {w}
                            </p>
                          ))}
                        </div>
                      ) : null}
                      {!dispatchSettings?.real_send_enabled ? (
                        <p className="mt-2 text-xs text-emerald-200">
                          Echte Sendung ist deaktiviert. Draft-only Mode ist aktiv.
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Noch keine Queue Items.</p>
          )}
        </Card>
      </div>

      {modalItemId && itemDispatch[modalItemId]?.dispatch ? (
        <ConfirmModal
          title={
            itemDispatch[modalItemId]?.dispatch?.dispatch_mode === "manual_send"
              ? "Kontrolliert senden — Bestätigung"
              : "Externen Draft erstellen — Bestätigung"
          }
          onClose={closeModal}
        >
          {(() => {
            const dispatch = itemDispatch[modalItemId]?.dispatch as OutreachDispatch;
            // Even if the backend dispatch_mode is 'manual_send', never show
            // send-flavored copy in the default UI unless real send is also
            // explicitly enabled — matches the hard rule that no real send
            // button ever appears by default.
            const isManualSend =
              dispatch.dispatch_mode === "manual_send" &&
              Boolean(dispatchSettings?.real_send_enabled);
            const acked = Boolean(dispatch.compliance_acknowledged_at);
            const ready = dispatch.dispatch_status === "ready";
            return (
              <div className="space-y-3 text-sm">
                <dl className="grid grid-cols-1 gap-1 text-xs text-slate-600 sm:grid-cols-2">
                  <p>Recipient: {dispatch.recipient_email ?? "—"}</p>
                  <p>Provider: {dispatch.provider}</p>
                  <p>Dispatch Mode: {dispatch.dispatch_mode}</p>
                  <p>Status: {dispatch.dispatch_status}</p>
                  <p>Compliance Ack: {acked ? "gesetzt" : "ausstehend"}</p>
                  <p>Final Confirmation: {dispatch.final_confirmation_at ? "gesetzt" : "ausstehend"}</p>
                </dl>
                {dispatch.subject_snapshot ? (
                  <div>
                    <p className="text-xs font-semibold text-slate-500">Subject Preview</p>
                    <p className="text-xs text-slate-700">{dispatch.subject_snapshot}</p>
                  </div>
                ) : null}
                {dispatch.body_preview_snapshot ? (
                  <div>
                    <p className="text-xs font-semibold text-slate-500">Body Preview</p>
                    <p className="whitespace-pre-wrap text-xs text-slate-700">
                      {dispatch.body_preview_snapshot}
                    </p>
                  </div>
                ) : null}

                {isManualSend ? (
                  <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">
                    Diese Aktion kann eine echte E-Mail senden, falls Real Send aktiviert
                    ist.
                  </div>
                ) : (
                  <div className="rounded-lg border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-200">
                    Es wird nur ein Draft erstellt, keine E-Mail gesendet.
                  </div>
                )}

                {!acked ? (
                  <div className="space-y-2 border-t border-slate-100 pt-3">
                    {COMPLIANCE_ACK_LABELS.map(({ key, label }) => (
                      <label key={key} className="flex items-start gap-2 text-xs text-slate-700">
                        <input
                          type="checkbox"
                          className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                          checked={ackForm[key]}
                          onChange={(e) =>
                            setAckForm({ ...ackForm, [key]: e.target.checked })
                          }
                        />
                        {label}
                      </label>
                    ))}
                    <Button loading={modalBusy} onClick={handleModalAcknowledge}>
                      Compliance bestätigen
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-2 border-t border-slate-100 pt-3">
                    <label className="flex items-start gap-2 text-xs text-slate-700">
                      <input
                        type="checkbox"
                        className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                        checked={confirmChecked}
                        onChange={(e) => setConfirmChecked(e.target.checked)}
                      />
                      Ich bestätige diese kontrollierte Aktion.
                    </label>
                    <Button
                      loading={modalBusy}
                      disabled={!confirmChecked}
                      onClick={handleModalConfirm}
                    >
                      {isManualSend ? "Kontrolliert senden" : "Externen Draft erstellen"}
                    </Button>
                    {!ready ? (
                      <p className="text-xs text-amber-200">
                        Hinweis: Readiness wird beim Bestätigen erneut geprüft.
                      </p>
                    ) : null}
                  </div>
                )}

                {modalError ? <p className="text-xs text-rose-400">{modalError}</p> : null}
                {dispatch.last_error ? (
                  <p className="text-xs text-rose-400">{dispatch.last_error}</p>
                ) : null}
                {dispatch.provider_url ? (
                  <a
                    href={dispatch.provider_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs underline hover:no-underline"
                  >
                    Provider-Link öffnen
                  </a>
                ) : null}
              </div>
            );
          })()}
        </ConfirmModal>
      ) : null}
    </RequireAuth>
  );
}
