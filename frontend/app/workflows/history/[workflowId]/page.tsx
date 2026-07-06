"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { ReviewEventTimeline } from "@/components/reviews/ReviewEventTimeline";
import { WorkflowCommentForm } from "@/components/reviews/WorkflowCommentForm";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ComplianceNotice } from "@/components/ui/ComplianceNotice";
import { JsonViewer } from "@/components/ui/JsonViewer";
import { Select } from "@/components/ui/Select";
import { REVIEW_STATUS_OPTIONS, REVIEW_STATUS_TONE } from "@/components/workflows/reviewStatus";
import { WorkflowResultSections } from "@/components/workflows/WorkflowResultSections";
import {
  ApiError,
  getSalesWorkflowRun,
  getWorkflowCrmLinks,
  listWorkflowReviewEvents,
  updateSalesWorkflowReviewStatus,
} from "@/lib/api";
import type {
  ReviewEvent,
  SalesWorkflowResponse,
  WorkflowCrmLinks,
  WorkflowReviewStatus,
  WorkflowRunDetail,
} from "@/lib/types";

function formatDate(value: string): string {
  return new Date(value).toLocaleString("de-DE");
}

function looksLikeSalesWorkflowResult(payload: Record<string, unknown>): boolean {
  return (
    "lead_research" in payload &&
    "company_intelligence" in payload &&
    "personalization" in payload &&
    "email_draft" in payload
  );
}

function StringList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">Keine Angaben.</p>;
  }
  return (
    <ul className="list-inside list-disc text-sm text-slate-700">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

export default function WorkflowHistoryDetailPage() {
  const params = useParams<{ workflowId: string }>();
  const workflowId = params.workflowId;

  const [run, setRun] = useState<WorkflowRunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [crmLinks, setCrmLinks] = useState<WorkflowCrmLinks | null>(null);
  const [crmLinksError, setCrmLinksError] = useState<string | null>(null);

  const [reviewEvents, setReviewEvents] = useState<ReviewEvent[]>([]);
  const [reviewEventsLoading, setReviewEventsLoading] = useState(true);
  const [reviewEventsError, setReviewEventsError] = useState<string | null>(null);

  const [selectedStatus, setSelectedStatus] = useState<WorkflowReviewStatus>("needs_review");
  const [updating, setUpdating] = useState(false);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [updateSuccess, setUpdateSuccess] = useState(false);

  async function loadRun() {
    setLoading(true);
    setError(null);
    try {
      const data = await getSalesWorkflowRun(workflowId);
      setRun(data);
      setSelectedStatus(data.review_status);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }

  async function loadCrmLinks() {
    setCrmLinksError(null);
    try {
      const data = await getWorkflowCrmLinks(workflowId);
      setCrmLinks(data);
    } catch (err) {
      setCrmLinksError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  async function loadReviewEvents() {
    setReviewEventsLoading(true);
    setReviewEventsError(null);
    try {
      const response = await listWorkflowReviewEvents(workflowId);
      setReviewEvents(response.items);
    } catch (err) {
      setReviewEventsError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setReviewEventsLoading(false);
    }
  }

  useEffect(() => {
    loadRun();
    loadCrmLinks();
    loadReviewEvents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflowId]);

  async function handleReviewStatusUpdate() {
    setUpdating(true);
    setUpdateError(null);
    setUpdateSuccess(false);
    try {
      const updated = await updateSalesWorkflowReviewStatus(workflowId, selectedStatus);
      setRun(updated);
      setUpdateSuccess(true);
    } catch (err) {
      setUpdateError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setUpdating(false);
    }
  }

  return (
    <RequireAuth>
    <div className="space-y-6">
      <div>
        <Link
          href="/workflows/history"
          className="text-sm font-medium text-brand-600 hover:text-brand-700"
        >
          ← Zurück zur Workflow History
        </Link>
        <h1 className="mt-2 text-xl font-semibold text-slate-900">Workflow-Details</h1>
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        <p>
          <strong>Wichtig:</strong> Workflows werden gespeichert, aber nichts
          wird automatisch versendet. Menschliche Prüfung bleibt erforderlich.
          Review Status löst keine Kontaktaufnahme aus.
        </p>
        <p className="mt-1">
          <strong>Mock-Modus aktiv:</strong> Ergebnisse können Platzhalter
          enthalten.
        </p>
      </div>

      <ComplianceNotice />

      {loading ? (
        <Card>
          <p className="text-sm text-slate-500">Lade Workflow…</p>
        </Card>
      ) : error ? (
        <Card>
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        </Card>
      ) : run ? (
        <>
          <Card title="Übersicht">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={run.status === "completed" ? "positive" : "warning"}>
                {run.status}
              </Badge>
              <Badge tone={REVIEW_STATUS_TONE[run.review_status]}>
                {run.review_status}
              </Badge>
              {run.confidence_score !== null ? (
                <Badge tone="info">
                  Confidence: {Math.round(run.confidence_score * 100)}%
                </Badge>
              ) : null}
            </div>
            <dl className="mt-4 space-y-1 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Workflow ID</dt>
                <dd className="font-mono text-slate-900">{run.id}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Firmenname</dt>
                <dd className="text-slate-900">{run.company_name}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Workflow-Typ</dt>
                <dd className="text-slate-900">{run.workflow_type}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Erstellt</dt>
                <dd className="text-slate-900">{formatDate(run.created_at)}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Aktualisiert</dt>
                <dd className="text-slate-900">{formatDate(run.updated_at)}</dd>
              </div>
            </dl>
          </Card>

          <Card title="CRM-Verknüpfungen">
            <p className="text-sm text-slate-600">
              Diese CRM-Verknüpfungen wurden automatisch gespeichert. Es wurde
              keine E-Mail gesendet.
            </p>
            {crmLinksError ? (
              <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {crmLinksError}
              </div>
            ) : crmLinks ? (
              <dl className="mt-3 space-y-1 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Company ID</dt>
                  <dd className="font-mono text-slate-900">
                    {crmLinks.company_id ?? "—"}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Lead ID</dt>
                  <dd className="font-mono text-slate-900">
                    {crmLinks.lead_id ?? "—"}
                  </dd>
                </div>
                {crmLinks.contact_id ? (
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Contact ID</dt>
                    <dd className="font-mono text-slate-900">{crmLinks.contact_id}</dd>
                  </div>
                ) : null}
                {crmLinks.email_draft_id ? (
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Email Draft ID</dt>
                    <dd className="font-mono text-slate-900">
                      {crmLinks.email_draft_id}
                    </dd>
                  </div>
                ) : null}
              </dl>
            ) : (
              <p className="mt-3 text-sm text-slate-500">Lade CRM-Verknüpfungen…</p>
            )}
            <p className="mt-3 text-sm">
              <Link
                href="/crm"
                className="font-medium text-brand-600 hover:text-brand-700"
              >
                Zu den CRM-Daten →
              </Link>
            </p>
          </Card>

          <Card title="Review Status ändern">
            <p className="text-sm text-slate-600">
              <strong>Approval ist nur interne Prüfung. Es wird keine E-Mail
              gesendet.</strong> Diese Aktion ändert ausschließlich den
              gespeicherten Review-Status — es erfolgt keine Kontaktaufnahme
              und kein Versand.
            </p>
            <div className="mt-3 flex flex-wrap items-end gap-4">
              <div className="w-56">
                <Select
                  label="Neuer Review Status"
                  value={selectedStatus}
                  options={REVIEW_STATUS_OPTIONS}
                  onChange={(e) =>
                    setSelectedStatus(e.target.value as WorkflowReviewStatus)
                  }
                />
              </div>
              <Button onClick={handleReviewStatusUpdate} loading={updating}>
                Aktualisieren
              </Button>
            </div>
            {updateSuccess ? (
              <p className="mt-3 text-sm text-emerald-700">
                Review Status wurde aktualisiert.
              </p>
            ) : null}
            {updateError ? (
              <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {updateError}
              </div>
            ) : null}
          </Card>

          <Card title="Kommentare & Review Timeline">
            <WorkflowCommentForm workflowId={workflowId} onAdded={loadReviewEvents} />
            <div className="mt-6 border-t border-slate-100 pt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Timeline
              </p>
              <div className="mt-3">
                {reviewEventsLoading ? (
                  <p className="text-sm text-slate-500">Lade Timeline…</p>
                ) : reviewEventsError ? (
                  <p className="text-sm text-rose-600">{reviewEventsError}</p>
                ) : (
                  <ReviewEventTimeline events={reviewEvents} />
                )}
              </div>
            </div>
          </Card>

          <Card title="Fehlende Informationen">
            <StringList items={run.missing_information} />
          </Card>

          <Card title="Compliance Notes">
            <StringList items={run.compliance_notes} />
          </Card>

          <Card title="Ergebnis">
            {looksLikeSalesWorkflowResult(run.result_payload) ? (
              <WorkflowResultSections
                data={run.result_payload as unknown as SalesWorkflowResponse}
              />
            ) : (
              <JsonViewer data={run.result_payload} />
            )}
          </Card>

          <Card title="Input Payload (Rohdaten)">
            <JsonViewer data={run.input_payload} />
          </Card>

          <Card title="Result Payload (Rohdaten)">
            <JsonViewer data={run.result_payload} />
          </Card>
        </>
      ) : null}
    </div>
    </RequireAuth>
  );
}
