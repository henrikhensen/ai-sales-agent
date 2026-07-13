"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ApiError, getAuditLogs } from "@/lib/api";
import type { AuditLog } from "@/lib/types";

function formatDate(value: string): string {
  return new Date(value).toLocaleString("de-DE");
}

const RESULT_TONE: Record<string, "positive" | "negative" | "warning" | "info" | "neutral"> = {
  success: "positive",
  failed: "negative",
  blocked: "negative",
  detected: "warning",
  started: "info",
  duplicate: "warning",
  cancelled: "neutral",
};

function AuditLogRow({ entry }: { entry: AuditLog }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-lg border border-slate-200 bg-surface px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-slate-900">{entry.action}</p>
          <p className="text-xs text-slate-500">{formatDate(entry.created_at)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge tone={RESULT_TONE[entry.result] ?? "neutral"}>{entry.result}</Badge>
          {entry.entity_type ? <Badge tone="neutral">{entry.entity_type}</Badge> : null}
        </div>
      </div>

      <p className="mt-2 text-sm text-slate-600">
        Actor: {entry.actor_user_id ?? "—"}
        {entry.actor_role ? ` (${entry.actor_role})` : ""}
      </p>
      {entry.reason ? (
        <p className="mt-1 text-sm text-slate-600">Reason: {entry.reason}</p>
      ) : null}

      {expanded ? (
        <div className="mt-3 space-y-1 border-t border-slate-100 pt-3 text-xs text-slate-600">
          <p>Entity ID: {entry.entity_id ?? "—"}</p>
          <p>Request ID: {entry.request_id ?? "—"}</p>
          {entry.metadata ? (
            <pre className="mt-1 overflow-x-auto rounded bg-slate-50 p-2 text-xs">
              {JSON.stringify(entry.metadata, null, 2)}
            </pre>
          ) : null}
        </div>
      ) : null}

      <div className="mt-3">
        <Button variant="ghost" onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Weniger" : "Details"}
        </Button>
      </div>
    </div>
  );
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [action, setAction] = useState("");
  const [entityType, setEntityType] = useState("");
  const [result, setResult] = useState("");
  const [actorUserId, setActorUserId] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getAuditLogs({
        action: action || undefined,
        entity_type: entityType || undefined,
        result: result || undefined,
        actor_user_id: actorUserId || undefined,
        date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
        date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
      });
      setLogs(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, [action, entityType, result, actorUserId, dateFrom, dateTo]);

  useEffect(() => {
    load();
  }, [load]);

  function handleFilterSubmit(event: React.FormEvent) {
    event.preventDefault();
    load();
  }

  return (
    <RequireRole
      allowedRoles={["admin"]}
      deniedMessage="Nur Admin-Konten haben Zugriff auf Audit Logs."
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Audit Logs</h1>
          <p className="mt-1 text-sm text-slate-600">
            System-weites Protokoll sicherheits- und compliance-relevanter
            Aktionen. Nur für Admin-Konten sichtbar. Zeigt keine Secrets,
            API Keys, Tokens, vollständige Email-Inhalte oder LLM-Prompts.
          </p>
        </div>

        <Card title="Filter">
          <form className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" onSubmit={handleFilterSubmit}>
            <Input
              label="Action"
              value={action}
              onChange={(e) => setAction(e.target.value)}
              placeholder="z. B. login"
            />
            <Input
              label="Entity Type"
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              placeholder="z. B. lead"
            />
            <Input
              label="Result"
              value={result}
              onChange={(e) => setResult(e.target.value)}
              placeholder="z. B. success, blocked"
            />
            <Input
              label="Actor User ID"
              value={actorUserId}
              onChange={(e) => setActorUserId(e.target.value)}
            />
            <Input
              label="Von"
              type="datetime-local"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
            <Input
              label="Bis"
              type="datetime-local"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
            <div className="sm:col-span-2 lg:col-span-3">
              <Button type="submit" loading={loading}>
                Filtern
              </Button>
            </div>
          </form>
        </Card>

        <Card title="Einträge">
          {loading ? (
            <p className="text-sm text-slate-500">Audit Logs werden geladen…</p>
          ) : error ? (
            <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </div>
          ) : logs && logs.length > 0 ? (
            <div className="space-y-3">
              {logs.map((entry) => (
                <AuditLogRow key={entry.id} entry={entry} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Keine Audit Logs gefunden.</p>
          )}
        </Card>
      </div>
    </RequireRole>
  );
}
