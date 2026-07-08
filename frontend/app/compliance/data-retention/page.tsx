"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  ApiError,
  createDataRetentionPolicy,
  deactivateDataRetentionPolicy,
  dryRunDataRetentionPolicy,
  getDataRetentionPolicies,
  getDataRetentionRuns,
  runDataRetentionPolicy,
  updateDataRetentionPolicy,
} from "@/lib/api";
import type {
  DataRetentionPolicy,
  DataRetentionRun,
  RetentionAction,
  RetentionEntityType,
} from "@/lib/types";

const ENTITY_TYPES: RetentionEntityType[] = [
  "lead",
  "company",
  "email_draft",
  "reply",
  "workflow_run",
  "audit_log",
  "do_not_contact",
  "external_draft",
  "outreach",
  "qualification",
  "sourcing_candidate",
];

const ACTIONS: RetentionAction[] = ["anonymize", "delete", "archive"];

const RUN_STATUS_TONE: Record<string, "positive" | "warning" | "negative" | "neutral"> = {
  running: "neutral",
  completed: "positive",
  failed: "negative",
  cancelled: "neutral",
};

export default function DataRetentionPage() {
  const [policies, setPolicies] = useState<DataRetentionPolicy[]>([]);
  const [runs, setRuns] = useState<DataRetentionRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    entity_type: "lead" as RetentionEntityType,
    retention_days: 365,
    action: "anonymize" as RetentionAction,
  });
  const [creating, setCreating] = useState(false);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDays, setEditDays] = useState(365);

  const [confirmPolicy, setConfirmPolicy] = useState<DataRetentionPolicy | null>(null);
  const [confirmChecked, setConfirmChecked] = useState(false);
  const [running, setRunning] = useState(false);
  const [lastRunResult, setLastRunResult] = useState<DataRetentionRun | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [policiesResult, runsResult] = await Promise.all([
        getDataRetentionPolicies(),
        getDataRetentionRuns(),
      ]);
      setPolicies(policiesResult.items);
      setRuns(runsResult.items);
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
      await createDataRetentionPolicy({
        name: form.name,
        entity_type: form.entity_type,
        retention_days: form.retention_days,
        action: form.action,
      });
      setForm({ name: "", entity_type: "lead", retention_days: 365, action: "anonymize" });
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setCreating(false);
    }
  }

  async function handleUpdateDays(policyId: string) {
    setActionError(null);
    try {
      await updateDataRetentionPolicy(policyId, { retention_days: editDays });
      setEditingId(null);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  async function handleDeactivate(policyId: string) {
    setActionError(null);
    try {
      await deactivateDataRetentionPolicy(policyId);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  async function handleDryRun(policyId: string) {
    setActionError(null);
    try {
      const run = await dryRunDataRetentionPolicy(policyId);
      setLastRunResult(run);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  async function handleConfirmedRun() {
    if (!confirmPolicy) return;
    setRunning(true);
    setActionError(null);
    try {
      const run = await runDataRetentionPolicy(confirmPolicy.id, { confirm: true });
      setLastRunResult(run);
      setConfirmPolicy(null);
      setConfirmChecked(false);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <RequireRole
      allowedRoles={["admin"]}
      deniedMessage="Nur Admin-Konten haben Zugriff auf Data Retention."
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Data Retention</h1>
          <p className="mt-1 text-sm text-slate-600">
            Richtlinien für die Aufbewahrung/Löschung von Daten. Dry Run ist
            Standard und verändert nie Daten. Anonymisierung ist die sichere
            Default-Aktion statt direkter Löschung.
          </p>
        </div>

        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          <p className="font-semibold">Achtung bei echten Runs.</p>
          <p className="mt-1">
            Ein echter (nicht Dry-Run) Lauf erfordert eine explizite Bestätigung
            und kann Daten anonymisieren oder löschen. Aktive Do-not-contact-
            Einträge werden nie angefasst, unabhängig vom Alter. Audit Logs
            werden nie gelöscht oder anonymisiert (Append-only per Design).
          </p>
        </div>

        {actionError ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {actionError}
          </div>
        ) : null}

        {loading ? (
          <p className="text-sm text-slate-500">Wird geladen…</p>
        ) : error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        ) : (
          <>
            <Card title="Neue Policy anlegen">
              <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleCreate}>
                <Input
                  label="Name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
                <Select
                  label="Entity Type"
                  value={form.entity_type}
                  options={ENTITY_TYPES.map((t) => ({ value: t, label: t }))}
                  onChange={(e) =>
                    setForm({ ...form, entity_type: e.target.value as RetentionEntityType })
                  }
                />
                <Input
                  label="Retention Days"
                  type="number"
                  min={1}
                  max={3650}
                  value={form.retention_days}
                  onChange={(e) =>
                    setForm({ ...form, retention_days: Number(e.target.value) })
                  }
                />
                <Select
                  label="Action"
                  value={form.action}
                  options={ACTIONS.map((a) => ({ value: a, label: a }))}
                  onChange={(e) =>
                    setForm({ ...form, action: e.target.value as RetentionAction })
                  }
                />
                <div className="sm:col-span-2">
                  <Button type="submit" loading={creating}>
                    Policy anlegen
                  </Button>
                </div>
              </form>
            </Card>

            <Card title="Policies">
              <div className="space-y-2">
                {policies.length === 0 ? (
                  <p className="text-sm text-slate-500">Noch keine Policies angelegt.</p>
                ) : null}
                {policies.map((policy) => (
                  <div
                    key={policy.id}
                    className="rounded-lg border border-slate-200 px-3 py-2"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <span className="text-sm font-semibold text-slate-900">
                          {policy.name}
                        </span>
                        <span className="ml-2 text-xs text-slate-500">
                          {policy.entity_type} · {policy.action}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge tone={policy.is_active ? "positive" : "neutral"}>
                          {policy.is_active ? "aktiv" : "deaktiviert"}
                        </Badge>
                        <Badge tone={policy.dry_run_default ? "info" : "warning"}>
                          {policy.dry_run_default ? "Dry Run Standard" : "Echter Lauf Standard"}
                        </Badge>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      {editingId === policy.id ? (
                        <>
                          <input
                            type="number"
                            className="w-24 rounded-lg border border-slate-300 px-2 py-1 text-sm"
                            value={editDays}
                            onChange={(e) => setEditDays(Number(e.target.value))}
                          />
                          <Button variant="secondary" onClick={() => handleUpdateDays(policy.id)}>
                            Speichern
                          </Button>
                          <Button variant="ghost" onClick={() => setEditingId(null)}>
                            Abbrechen
                          </Button>
                        </>
                      ) : (
                        <>
                          <span className="text-xs text-slate-500">
                            {policy.retention_days} Tage
                          </span>
                          <Button
                            variant="ghost"
                            onClick={() => {
                              setEditingId(policy.id);
                              setEditDays(policy.retention_days);
                            }}
                          >
                            Tage bearbeiten
                          </Button>
                        </>
                      )}
                      <Button variant="secondary" onClick={() => handleDryRun(policy.id)}>
                        Dry Run starten
                      </Button>
                      <Button
                        className="bg-rose-600 hover:bg-rose-700 disabled:bg-rose-300"
                        disabled={!policy.is_active}
                        onClick={() => setConfirmPolicy(policy)}
                      >
                        Echten Lauf starten
                      </Button>
                      {policy.is_active ? (
                        <Button variant="ghost" onClick={() => handleDeactivate(policy.id)}>
                          Deaktivieren
                        </Button>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            {lastRunResult ? (
              <Card title="Letztes Run-Ergebnis">
                <div className="flex items-center gap-2">
                  <Badge tone={lastRunResult.dry_run ? "info" : "warning"}>
                    {lastRunResult.dry_run ? "Dry Run" : "Echter Lauf"}
                  </Badge>
                  <Badge tone={RUN_STATUS_TONE[lastRunResult.status] ?? "neutral"}>
                    {lastRunResult.status}
                  </Badge>
                </div>
                <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-4">
                  <div>
                    <dt className="text-slate-500">Gescannt</dt>
                    <dd className="text-slate-900">{lastRunResult.total_scanned}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Eligible</dt>
                    <dd className="text-slate-900">{lastRunResult.total_eligible}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Verarbeitet</dt>
                    <dd className="text-slate-900">{lastRunResult.total_processed}</dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Fehlgeschlagen</dt>
                    <dd className="text-slate-900">{lastRunResult.total_failed}</dd>
                  </div>
                </dl>
                {lastRunResult.warnings.length > 0 ? (
                  <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    {lastRunResult.warnings.map((w) => (
                      <p key={w}>{w}</p>
                    ))}
                  </div>
                ) : null}
              </Card>
            ) : null}

            <Card title="Run Historie">
              <div className="space-y-2">
                {runs.length === 0 ? (
                  <p className="text-sm text-slate-500">Noch keine Runs.</p>
                ) : null}
                {runs.map((run) => (
                  <div
                    key={run.id}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  >
                    <span>
                      {run.entity_type} · {run.action} ·{" "}
                      {run.dry_run ? "Dry Run" : "Echter Lauf"}
                    </span>
                    <div className="flex items-center gap-2">
                      <Badge tone={RUN_STATUS_TONE[run.status] ?? "neutral"}>
                        {run.status}
                      </Badge>
                      <span className="text-xs text-slate-500">
                        scanned={run.total_scanned} processed={run.total_processed}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </>
        )}

        {confirmPolicy ? (
          <ConfirmModal
            title={`Echten Lauf starten: ${confirmPolicy.name}`}
            onClose={() => {
              setConfirmPolicy(null);
              setConfirmChecked(false);
            }}
          >
            <div className="space-y-3 text-sm text-slate-700">
              <p>
                Diese Aktion führt <strong>{confirmPolicy.action}</strong> auf allen
                Datensätzen vom Typ <strong>{confirmPolicy.entity_type}</strong> aus, die
                älter als {confirmPolicy.retention_days} Tage sind. Dies ist keine
                Vorschau — Daten werden tatsächlich verändert.
              </p>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={confirmChecked}
                  onChange={(e) => setConfirmChecked(e.target.checked)}
                />
                Ich bestätige, dass ich diesen echten Lauf bewusst starten möchte.
              </label>
              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setConfirmPolicy(null);
                    setConfirmChecked(false);
                  }}
                >
                  Abbrechen
                </Button>
                <Button
                  className="bg-rose-600 hover:bg-rose-700 disabled:bg-rose-300"
                  disabled={!confirmChecked}
                  loading={running}
                  onClick={handleConfirmedRun}
                >
                  Jetzt ausführen
                </Button>
              </div>
            </div>
          </ConfirmModal>
        ) : null}
      </div>
    </RequireRole>
  );
}
