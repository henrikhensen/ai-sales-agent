"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ComplianceNotice } from "@/components/ui/ComplianceNotice";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { REVIEW_STATUS_OPTIONS, REVIEW_STATUS_TONE } from "@/components/workflows/reviewStatus";
import { ApiError, listSalesWorkflowRuns } from "@/lib/api";
import type { WorkflowReviewStatus, WorkflowRunSummary } from "@/lib/types";

function formatDate(value: string): string {
  return new Date(value).toLocaleString("de-DE");
}

export default function WorkflowHistoryPage() {
  const [items, setItems] = useState<WorkflowRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [companyNameFilter, setCompanyNameFilter] = useState("");
  const [reviewStatusFilter, setReviewStatusFilter] = useState<WorkflowReviewStatus | "">("");

  async function loadRuns() {
    setLoading(true);
    setError(null);
    try {
      const response = await listSalesWorkflowRuns({
        limit: 100,
        offset: 0,
        company_name: companyNameFilter.trim() || undefined,
        review_status: reviewStatusFilter || undefined,
      });
      setItems(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRuns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleFilterSubmit(event: React.FormEvent) {
    event.preventDefault();
    loadRuns();
  }

  return (
    <RequireAuth>
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Workflow History</h1>
        <p className="mt-1 text-sm text-slate-600">
          Übersicht über gespeicherte Sales-Workflow-Läufe.
        </p>
      </div>

      <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
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

      <Card title="Filter">
        <form className="flex flex-wrap items-end gap-4" onSubmit={handleFilterSubmit}>
          <div className="w-56">
            <Input
              label="Firmenname"
              value={companyNameFilter}
              onChange={(e) => setCompanyNameFilter(e.target.value)}
              placeholder="z. B. Acme"
            />
          </div>
          <div className="w-56">
            <Select
              label="Review Status"
              value={reviewStatusFilter}
              options={[{ value: "", label: "Alle" }, ...REVIEW_STATUS_OPTIONS]}
              onChange={(e) =>
                setReviewStatusFilter(e.target.value as WorkflowReviewStatus | "")
              }
            />
          </div>
          <Button type="submit" loading={loading}>
            Filtern
          </Button>
        </form>
      </Card>

      <Card title="Gespeicherte Runs">
        {loading ? (
          <p className="text-sm text-slate-500">Lade Workflow-Läufe…</p>
        ) : error ? (
          <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
            {error}
          </div>
        ) : items.length === 0 ? (
          <p className="text-sm text-slate-500">Noch keine Workflow-Läufe gespeichert.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-400">
                <tr>
                  <th className="pb-2 pr-4">Firmenname</th>
                  <th className="pb-2 pr-4">Typ</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Review Status</th>
                  <th className="pb-2 pr-4">Confidence</th>
                  <th className="pb-2 pr-4">Erstellt</th>
                  <th className="pb-2 pr-4">Aktualisiert</th>
                  <th className="pb-2"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {items.map((run) => (
                  <tr key={run.id}>
                    <td className="py-2 pr-4 font-medium text-slate-900">
                      {run.company_name}
                    </td>
                    <td className="py-2 pr-4 text-slate-600">{run.workflow_type}</td>
                    <td className="py-2 pr-4 text-slate-600">{run.status}</td>
                    <td className="py-2 pr-4">
                      <Badge tone={REVIEW_STATUS_TONE[run.review_status]}>
                        {run.review_status}
                      </Badge>
                    </td>
                    <td className="py-2 pr-4 text-slate-600">
                      {run.confidence_score !== null
                        ? `${Math.round(run.confidence_score * 100)}%`
                        : "—"}
                    </td>
                    <td className="py-2 pr-4 text-slate-600">
                      {formatDate(run.created_at)}
                    </td>
                    <td className="py-2 pr-4 text-slate-600">
                      {formatDate(run.updated_at)}
                    </td>
                    <td className="py-2">
                      <Link
                        href={`/workflows/history/${run.id}`}
                        className="font-medium text-brand-600 hover:text-brand-700"
                      >
                        Details ansehen →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
    </RequireAuth>
  );
}
