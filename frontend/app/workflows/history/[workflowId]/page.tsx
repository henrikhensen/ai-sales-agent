"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { JsonViewer } from "@/components/ui/JsonViewer";
import { Select } from "@/components/ui/Select";
import { REVIEW_STATUS_OPTIONS, REVIEW_STATUS_TONE } from "@/components/workflows/reviewStatus";
import { WorkflowResultSections } from "@/components/workflows/WorkflowResultSections";
import { ApiError, getSalesWorkflowRun, updateSalesWorkflowReviewStatus } from "@/lib/api";
import type {
  SalesWorkflowResponse,
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

  useEffect(() => {
    loadRun();
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
  );
}
