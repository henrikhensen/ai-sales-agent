"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { Select } from "@/components/ui/Select";
import {
  ApiError,
  getCrmPipeline,
  listCrmCompanies,
  syncLeadReplies,
  updateLeadPipelineStatus,
} from "@/lib/api";
import { canSetAnyPipelineStatus, canSyncReplies, isReviewer } from "@/lib/roles";
import type {
  Company,
  LeadPipelineSummary,
  PipelineBoardResponse,
  PipelineStatus,
} from "@/lib/types";

const PIPELINE_STATUS_ORDER: PipelineStatus[] = [
  "new",
  "research_completed",
  "draft_created",
  "in_review",
  "approved",
  "rejected",
  "archived",
];

const PIPELINE_STATUS_LABELS: Record<PipelineStatus, string> = {
  new: "New",
  research_completed: "Research Completed",
  draft_created: "Draft Created",
  in_review: "In Review",
  approved: "Approved",
  rejected: "Rejected",
  archived: "Archived",
};

const PIPELINE_STATUS_TONE: Record<
  PipelineStatus,
  "neutral" | "positive" | "negative" | "warning" | "info"
> = {
  new: "neutral",
  research_completed: "info",
  draft_created: "warning",
  in_review: "info",
  approved: "positive",
  rejected: "negative",
  archived: "neutral",
};

// Reviewer accounts may only move a lead into these three statuses — the
// backend enforces the identical restriction on
// PATCH /api/v1/crm/leads/{lead_id}/pipeline-status.
const REVIEWER_ALLOWED_STATUSES: PipelineStatus[] = ["in_review", "approved", "rejected"];

const ALL_STATUS_OPTIONS = PIPELINE_STATUS_ORDER.map((status) => ({
  value: status,
  label: PIPELINE_STATUS_LABELS[status],
}));

function formatDate(value: string | null): string {
  if (!value) {
    return "Nicht verfügbar";
  }
  return new Date(value).toLocaleString("de-DE");
}

interface LeadCardProps {
  lead: LeadPipelineSummary;
  companyName: string | null;
  canChangeStatus: boolean;
  statusOptions: { value: string; label: string }[];
  onStatusChanged: () => void;
  canSyncLeadReplies: boolean;
}

function LeadCard({
  lead,
  companyName,
  canChangeStatus,
  statusOptions,
  onStatusChanged,
  canSyncLeadReplies,
}: LeadCardProps) {
  const [selectedStatus, setSelectedStatus] = useState<PipelineStatus>(lead.pipeline_status);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [syncingReplies, setSyncingReplies] = useState(false);
  const [replySyncMessage, setReplySyncMessage] = useState<string | null>(null);
  const [replySyncError, setReplySyncError] = useState<string | null>(null);

  async function handleSyncReplies() {
    setSyncingReplies(true);
    setReplySyncMessage(null);
    setReplySyncError(null);
    try {
      const result = await syncLeadReplies(lead.id);
      setReplySyncMessage(result.message);
    } catch (err) {
      setReplySyncError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setSyncingReplies(false);
    }
  }

  // Keeps the select in sync once the board reloads with a fresh status —
  // this component instance stays mounted across reloads (same lead.id key).
  useEffect(() => {
    setSelectedStatus(lead.pipeline_status);
  }, [lead.pipeline_status]);

  async function handleUpdate() {
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      await updateLeadPipelineStatus(lead.id, selectedStatus);
      setSuccess(true);
      onStatusChanged();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Keine Berechtigung für diese Aktion.");
      } else {
        setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card className="space-y-3">
      <div className="flex items-start justify-between gap-2">
        <p className="break-all font-mono text-xs text-slate-500">{lead.id}</p>
        <Badge tone={PIPELINE_STATUS_TONE[lead.pipeline_status]}>
          {PIPELINE_STATUS_LABELS[lead.pipeline_status]}
        </Badge>
      </div>
      <dl className="space-y-1 text-sm">
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Company</dt>
          <dd className="text-right text-slate-900">{companyName ?? "Nicht verfügbar"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Score</dt>
          <dd className="text-slate-900">{lead.score}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Erstellt</dt>
          <dd className="text-slate-900">{formatDate(lead.created_at)}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Aktualisiert</dt>
          <dd className="text-slate-900">{formatDate(lead.pipeline_updated_at)}</dd>
        </div>
      </dl>

      {canChangeStatus ? (
        <div className="space-y-2 border-t border-slate-100 pt-3">
          <Select
            label="Pipeline Status"
            value={selectedStatus}
            options={statusOptions}
            onChange={(e) => setSelectedStatus(e.target.value as PipelineStatus)}
          />
          <Button
            variant="secondary"
            onClick={handleUpdate}
            loading={saving}
            disabled={selectedStatus === lead.pipeline_status}
          >
            Status aktualisieren
          </Button>
          {success ? (
            <p className="text-xs text-emerald-300">Status wurde aktualisiert.</p>
          ) : null}
          {error ? <p className="text-xs text-rose-400">{error}</p> : null}
        </div>
      ) : null}

      <div className="space-y-1 border-t border-slate-100 pt-3">
        <div className="flex flex-wrap items-center gap-2">
          {canSyncLeadReplies ? (
            <Button variant="ghost" onClick={handleSyncReplies} loading={syncingReplies}>
              Replies synchronisieren
            </Button>
          ) : null}
          <Link href="/replies" className="text-xs text-brand-600 underline">
            Reply Inbox öffnen
          </Link>
        </div>
        {replySyncMessage ? (
          <p className="text-xs text-emerald-300">{replySyncMessage}</p>
        ) : null}
        {replySyncError ? <p className="text-xs text-rose-400">{replySyncError}</p> : null}
      </div>
    </Card>
  );
}

export default function CrmPipelinePage() {
  const { currentUser } = useAuth();
  const canChangeAnyStatus = canSetAnyPipelineStatus(currentUser);
  const canChangeReviewAdjacentStatus = isReviewer(currentUser);
  const canChangeStatus = canChangeAnyStatus || canChangeReviewAdjacentStatus;
  const canSyncLeadReplies = canSyncReplies(currentUser);
  const statusOptions = canChangeAnyStatus
    ? ALL_STATUS_OPTIONS
    : ALL_STATUS_OPTIONS.filter((option) =>
        REVIEWER_ALLOWED_STATUSES.includes(option.value as PipelineStatus)
      );

  const [board, setBoard] = useState<PipelineBoardResponse | null>(null);
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBoard = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [boardResponse, companiesResponse] = await Promise.all([
        getCrmPipeline(),
        listCrmCompanies(),
      ]);
      setBoard(boardResponse);
      setCompanies(companiesResponse);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBoard();
  }, [loadBoard]);

  const companyNameById = new Map(companies.map((company) => [company.id, company.name]));
  const columnsByStatus = new Map(
    (board?.columns ?? []).map((column) => [column.pipeline_status, column])
  );

  return (
    <RequireAuth>
      <div className="space-y-6">
        <SectionHeader
          eyebrow="Leads"
          title="Lead Pipeline"
          description="Leads gruppiert nach Pipeline-Stufe, wie sie der Sales Workflow und die interne Prüfung durchlaufen."
        />

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-none border border-emerald-400/25 bg-emerald-400/10 px-4 py-2.5 text-xs font-medium text-emerald-200">
          <span>Kein E-Mail-Versand durch Statuswechsel</span>
          <span aria-hidden="true">·</span>
          <span>Approved = interne Prüfung, nicht Versand</span>
          <span aria-hidden="true">·</span>
          <span>Keine automatische Kontaktaufnahme</span>
          <span aria-hidden="true">·</span>
          <span>Email Drafts bleiben Entwürfe</span>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Pipeline wird geladen…</p>
        ) : error ? (
          <div className="rounded-none border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
            {error}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {PIPELINE_STATUS_ORDER.map((status) => {
              const column = columnsByStatus.get(status);
              const leads = column?.leads ?? [];
              return (
                <div key={status} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm font-semibold text-slate-900">
                      {PIPELINE_STATUS_LABELS[status]}
                    </h2>
                    <Badge tone={PIPELINE_STATUS_TONE[status]}>{leads.length}</Badge>
                  </div>
                  <div className="space-y-3">
                    {leads.length === 0 ? (
                      <p className="text-xs text-slate-400">Keine Leads.</p>
                    ) : (
                      leads.map((lead) => (
                        <LeadCard
                          key={lead.id}
                          lead={lead}
                          companyName={companyNameById.get(lead.company_id) ?? null}
                          canChangeStatus={canChangeStatus}
                          statusOptions={statusOptions}
                          onStatusChanged={loadBoard}
                          canSyncLeadReplies={canSyncLeadReplies}
                        />
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </RequireAuth>
  );
}
