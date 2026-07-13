"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  ApiError,
  completeDataRequest,
  createDataRequest,
  exportComplianceData,
  exportDataRequest,
  getDataRequests,
  prepareAnonymizeDataRequest,
  updateDataRequest,
} from "@/lib/api";
import type {
  DataExportResponse,
  DataRequestType,
  DataSubjectRequest,
} from "@/lib/types";

const REQUEST_TYPES: DataRequestType[] = [
  "export",
  "delete",
  "anonymize",
  "do_not_contact",
  "correction",
];

const STATUS_TONE: Record<string, "positive" | "warning" | "negative" | "neutral"> = {
  open: "neutral",
  in_progress: "warning",
  completed: "positive",
  rejected: "negative",
  cancelled: "neutral",
};

export default function DataRequestsPage() {
  const [requests, setRequests] = useState<DataSubjectRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [exportPreview, setExportPreview] = useState<DataExportResponse | null>(null);

  const [form, setForm] = useState({
    request_type: "export" as DataRequestType,
    subject_email: "",
    subject_domain: "",
    subject_name: "",
    notes: "",
  });
  const [creating, setCreating] = useState(false);

  const [exportForm, setExportForm] = useState({ email: "", domain: "", name: "" });
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDataRequests();
      setRequests(result.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setCreating(true);
    setActionError(null);
    try {
      await createDataRequest({
        request_type: form.request_type,
        subject_email: form.subject_email || null,
        subject_domain: form.subject_domain || null,
        subject_name: form.subject_name || null,
        notes: form.notes || null,
      });
      setForm({
        request_type: "export",
        subject_email: "",
        subject_domain: "",
        subject_name: "",
        notes: "",
      });
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setCreating(false);
    }
  }

  async function handleExportForRequest(requestId: string) {
    setBusyId(requestId);
    setActionError(null);
    try {
      const detail = await exportDataRequest(requestId);
      setExportPreview(detail.export);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusyId(null);
    }
  }

  async function handlePrepareAnonymize(requestId: string) {
    setBusyId(requestId);
    setActionError(null);
    try {
      await prepareAnonymizeDataRequest(requestId);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleComplete(requestId: string) {
    setBusyId(requestId);
    setActionError(null);
    try {
      await completeDataRequest(requestId);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleStatusChange(requestId: string, status: string) {
    setBusyId(requestId);
    setActionError(null);
    try {
      await updateDataRequest(requestId, { status: status as DataSubjectRequest["status"] });
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleExportSearch(event: React.FormEvent) {
    event.preventDefault();
    setExporting(true);
    setExportError(null);
    try {
      const result = await exportComplianceData({
        email: exportForm.email || null,
        domain: exportForm.domain || null,
        name: exportForm.name || null,
      });
      setExportPreview(result);
    } catch (err) {
      setExportError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <RequireRole
      allowedRoles={["admin"]}
      deniedMessage="Nur Admin-Konten haben Zugriff auf Data Subject Requests."
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Data Subject Requests</h1>
          <p className="mt-1 text-sm text-slate-600">
            Anfragen von oder über Betroffene (Export, Löschung, Anonymisierung,
            Do-not-contact, Korrektur). Erstellen sendet nie automatisch eine
            E-Mail an die betroffene Person.
          </p>
        </div>

        {actionError ? (
          <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
            {actionError}
          </div>
        ) : null}

        <Card title="Neue Anfrage erstellen">
          <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleCreate}>
            <Select
              label="Request Type"
              value={form.request_type}
              options={REQUEST_TYPES.map((t) => ({ value: t, label: t }))}
              onChange={(e) =>
                setForm({ ...form, request_type: e.target.value as DataRequestType })
              }
            />
            <Input
              label="Subject Email"
              value={form.subject_email}
              onChange={(e) => setForm({ ...form, subject_email: e.target.value })}
            />
            <Input
              label="Subject Domain"
              value={form.subject_domain}
              onChange={(e) => setForm({ ...form, subject_domain: e.target.value })}
            />
            <Input
              label="Subject Name"
              value={form.subject_name}
              onChange={(e) => setForm({ ...form, subject_name: e.target.value })}
            />
            <div className="sm:col-span-2">
              <Input
                label="Notes"
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
              />
            </div>
            <div className="sm:col-span-2">
              <Button type="submit" loading={creating}>
                Anfrage erstellen
              </Button>
            </div>
          </form>
        </Card>

        {loading ? (
          <p className="text-sm text-slate-500">Wird geladen…</p>
        ) : error ? (
          <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
            {error}
          </div>
        ) : (
          <Card title="Anfragen">
            <div className="space-y-2">
              {requests.length === 0 ? (
                <p className="text-sm text-slate-500">Noch keine Anfragen.</p>
              ) : null}
              {requests.map((req) => (
                <div key={req.id} className="rounded-lg border border-slate-200 px-3 py-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-sm">
                      <span className="font-semibold text-slate-900">
                        {req.request_type}
                      </span>
                      <span className="ml-2 text-slate-500">
                        {req.subject_email ?? req.subject_domain ?? req.subject_name}
                      </span>
                    </div>
                    <Badge tone={STATUS_TONE[req.status] ?? "neutral"}>{req.status}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    Erstellt: {new Date(req.created_at).toLocaleString("de-DE")}
                    {req.completed_at
                      ? ` · Abgeschlossen: ${new Date(req.completed_at).toLocaleString("de-DE")}`
                      : ""}
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <Button
                      variant="secondary"
                      loading={busyId === req.id}
                      onClick={() => handleExportForRequest(req.id)}
                    >
                      Export ausführen
                    </Button>
                    <Button
                      variant="secondary"
                      loading={busyId === req.id}
                      onClick={() => handlePrepareAnonymize(req.id)}
                    >
                      Anonymize vorbereiten
                    </Button>
                    {req.status !== "completed" ? (
                      <Button
                        variant="secondary"
                        loading={busyId === req.id}
                        onClick={() => handleComplete(req.id)}
                      >
                        Abschließen
                      </Button>
                    ) : null}
                    {req.status === "open" ? (
                      <Button
                        variant="ghost"
                        loading={busyId === req.id}
                        onClick={() => handleStatusChange(req.id, "rejected")}
                      >
                        Ablehnen
                      </Button>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        <Card title="Data Export (Suche)">
          <div className="mb-3 rounded-lg border border-amber-400/25 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
            Export kann personenbezogene Daten enthalten und darf nur für einen
            berechtigten, legitimen Zweck verwendet werden. Nur für Admins sichtbar.
            Enthält nie Secrets, Tokens oder API Keys.
          </div>
          <form className="grid gap-4 sm:grid-cols-3" onSubmit={handleExportSearch}>
            <Input
              label="Email"
              value={exportForm.email}
              onChange={(e) => setExportForm({ ...exportForm, email: e.target.value })}
            />
            <Input
              label="Domain"
              value={exportForm.domain}
              onChange={(e) => setExportForm({ ...exportForm, domain: e.target.value })}
            />
            <Input
              label="Name"
              value={exportForm.name}
              onChange={(e) => setExportForm({ ...exportForm, name: e.target.value })}
            />
            <div className="sm:col-span-3">
              <Button type="submit" loading={exporting}>
                Export starten
              </Button>
            </div>
          </form>
          {exportError ? (
            <p className="mt-2 text-sm text-rose-400">{exportError}</p>
          ) : null}
          {exportPreview ? (
            <div className="mt-4">
              <p className="mb-2 text-sm text-slate-600">{exportPreview.message}</p>
              <pre className="max-h-96 overflow-auto rounded-lg border border-white/10 bg-black/30 p-3 text-xs text-muted/75">
                {JSON.stringify(exportPreview, null, 2)}
              </pre>
            </div>
          ) : null}
        </Card>
      </div>
    </RequireRole>
  );
}
