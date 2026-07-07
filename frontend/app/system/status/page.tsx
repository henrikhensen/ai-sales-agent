"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ApiError, getBackupStatus, getMetrics, getSystemStatus } from "@/lib/api";
import type { BackupStatus, Metrics, SystemStatus } from "@/lib/types";

function formatDate(value: string | null): string {
  if (!value) {
    return "Nicht verfügbar";
  }
  return new Date(value).toLocaleString("de-DE");
}

function StatusBadge({ up }: { up: boolean }) {
  return <Badge tone={up ? "positive" : "negative"}>{up ? "up" : "down"}</Badge>;
}

function SafeModeBadge({ safe }: { safe: boolean }) {
  return (
    <Badge tone={safe ? "positive" : "warning"}>
      {safe ? "Mock / Safe Mode" : "Real Mode"}
    </Badge>
  );
}

export default function SystemStatusPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [backup, setBackup] = useState<BackupStatus | null>(null);
  const [backupError, setBackupError] = useState<string | null>(null);

  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [metricsError, setMetricsError] = useState<string | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setStatusError(null);
    setBackupError(null);
    try {
      const result = await getSystemStatus();
      setStatus(result);
    } catch (err) {
      setStatusError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
    try {
      const result = await getBackupStatus();
      setBackup(result);
    } catch (err) {
      setBackupError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleLoadMetrics() {
    setMetricsLoading(true);
    setMetricsError(null);
    try {
      const result = await getMetrics();
      setMetrics(result);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setMetricsError("Metrics sind deaktiviert (ENABLE_METRICS=false).");
      } else {
        setMetricsError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
      }
    } finally {
      setMetricsLoading(false);
    }
  }

  return (
    <RequireRole
      allowedRoles={["admin"]}
      deniedMessage="Nur Admin-Konten haben Zugriff auf System Status."
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">System Status</h1>
          <p className="mt-1 text-sm text-slate-600">
            Deployment-, Monitoring- und Backup-Übersicht. Nur sichtbar für
            Admin-Konten. Zeigt keine Secrets, API Keys oder Tokens.
          </p>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Status wird geladen…</p>
        ) : (
          <>
            {statusError ? (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {statusError}
              </div>
            ) : status ? (
              <>
                {status.production_warnings.length > 0 ? (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                    <p className="font-medium">Production Warnungen</p>
                    <ul className="mt-1 list-inside list-disc space-y-0.5">
                      {status.production_warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                <Card title="Anwendung">
                  <dl className="grid gap-3 text-sm sm:grid-cols-2">
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">App</dt>
                      <dd className="text-slate-900">
                        {status.app_name} v{status.app_version}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Environment</dt>
                      <dd className="text-slate-900">{status.app_env}</dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Database</dt>
                      <dd><StatusBadge up={status.database_status === "up"} /></dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Redis</dt>
                      <dd><StatusBadge up={status.redis_status === "up"} /></dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Request Logging</dt>
                      <dd>
                        <Badge tone={status.request_logging_enabled ? "positive" : "neutral"}>
                          {status.request_logging_enabled ? "enabled" : "disabled"}
                        </Badge>
                      </dd>
                    </div>
                  </dl>
                </Card>

                <Card title="Provider / Safe Mode">
                  <dl className="grid gap-3 text-sm sm:grid-cols-2">
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">LLM Provider</dt>
                      <dd className="flex items-center gap-2 text-slate-900">
                        {status.llm_provider}
                        <SafeModeBadge safe={!status.llm_real_calls_enabled} />
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Email Integration</dt>
                      <dd className="flex items-center gap-2 text-slate-900">
                        {status.email_integration_provider}
                        <SafeModeBadge safe={!status.email_real_drafts_enabled} />
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Reply Tracking</dt>
                      <dd className="flex items-center gap-2 text-slate-900">
                        {status.reply_tracking_provider}
                        <SafeModeBadge safe={!status.reply_real_reads_enabled} />
                      </dd>
                    </div>
                  </dl>
                </Card>
              </>
            ) : null}

            {backupError ? (
              <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {backupError}
              </div>
            ) : backup ? (
              <Card title="Backups">
                <dl className="grid gap-3 text-sm sm:grid-cols-2">
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Enabled</dt>
                    <dd>
                      <Badge tone={backup.backups_enabled ? "positive" : "neutral"}>
                        {backup.backups_enabled ? "enabled" : "disabled"}
                      </Badge>
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Backup Dir</dt>
                    <dd className="text-slate-900">{backup.backup_dir}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Retention</dt>
                    <dd className="text-slate-900">{backup.retention_days} Tage</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Letztes Backup</dt>
                    <dd className="text-slate-900">
                      {formatDate(backup.latest_backup_time)}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Datei</dt>
                    <dd className="text-slate-900">
                      {backup.latest_backup_file_name ?? "—"}
                    </dd>
                  </div>
                </dl>
                <p className="mt-3 text-xs text-slate-500">
                  Kein Download hier — Backups per{" "}
                  <code>scripts/backup_db.ps1</code> /{" "}
                  <code>scripts/backup_db.sh</code> erstellen.
                </p>
              </Card>
            ) : null}

            <Card title="Metrics">
              {status && !status.metrics_enabled ? (
                <p className="text-sm text-slate-500">
                  Metrics sind deaktiviert (ENABLE_METRICS=false).
                </p>
              ) : (
                <div className="space-y-3">
                  <Button variant="secondary" onClick={handleLoadMetrics} loading={metricsLoading}>
                    Metrics laden
                  </Button>
                  {metricsError ? (
                    <p className="text-sm text-rose-600">{metricsError}</p>
                  ) : metrics ? (
                    <dl className="grid gap-2 text-sm sm:grid-cols-2">
                      <div className="flex justify-between gap-4">
                        <dt className="text-slate-500">Requests</dt>
                        <dd className="text-slate-900">{metrics.request_count}</dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-slate-500">Fehler (4xx/5xx)</dt>
                        <dd className="text-slate-900">{metrics.request_error_count}</dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-slate-500">Ø Antwortzeit</dt>
                        <dd className="text-slate-900">
                          {metrics.average_response_time_ms} ms
                        </dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-slate-500">Workflow Runs</dt>
                        <dd className="text-slate-900">{metrics.workflow_run_count}</dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-slate-500">Email Drafts</dt>
                        <dd className="text-slate-900">{metrics.email_draft_count}</dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-slate-500">Replies</dt>
                        <dd className="text-slate-900">{metrics.reply_count}</dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-slate-500">External Drafts</dt>
                        <dd className="text-slate-900">
                          {metrics.external_draft_created_count}
                        </dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-slate-500">Do-not-contact Blocks</dt>
                        <dd className="text-slate-900">
                          {metrics.do_not_contact_block_count}
                        </dd>
                      </div>
                      <div className="flex justify-between gap-4">
                        <dt className="text-slate-500">LLM Tests</dt>
                        <dd className="text-slate-900">{metrics.llm_test_count}</dd>
                      </div>
                    </dl>
                  ) : null}
                </div>
              )}
            </Card>
          </>
        )}
      </div>
    </RequireRole>
  );
}
