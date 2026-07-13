"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ApiError, getComplianceStatus } from "@/lib/api";
import type { ComplianceStatus } from "@/lib/types";

function StatusBadge({
  active,
  activeLabel,
  inactiveLabel,
}: {
  active: boolean;
  activeLabel: string;
  inactiveLabel: string;
}) {
  return (
    <Badge tone={active ? "positive" : "neutral"}>
      {active ? activeLabel : inactiveLabel}
    </Badge>
  );
}

function SafeModeBadge({ safe }: { safe: boolean }) {
  return (
    <Badge tone={safe ? "positive" : "warning"}>
      {safe ? "Mock / Safe Mode" : "Real Mode"}
    </Badge>
  );
}

export default function ComplianceStatusPage() {
  const [status, setStatus] = useState<ComplianceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getComplianceStatus();
      setStatus(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <RequireRole
      allowedRoles={["admin", "sales", "reviewer"]}
      deniedMessage="Nur Admin-, Sales- und Reviewer-Konten haben Zugriff auf den Compliance Status."
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Compliance Status</h1>
          <p className="mt-1 text-sm text-slate-600">
            Sicherer Überblick über alle Schutzmechanismen dieses Systems.
            Zeigt keine Secrets, API Keys oder Tokens.
          </p>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Status wird geladen…</p>
        ) : error ? (
          <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
            {error}
          </div>
        ) : status ? (
          <>
            <div className="rounded-lg border border-emerald-400/25 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-200">
              <p className="font-medium">{status.message}</p>
            </div>

            {status.warnings.length > 0 ? (
              <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
                <p className="font-medium">Warnungen</p>
                <ul className="mt-1 list-inside list-disc space-y-0.5">
                  {status.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            <Card title="Kernschutzmechanismen">
              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Do-not-contact</dt>
                  <dd>
                    <StatusBadge
                      active={status.do_not_contact_enabled}
                      activeLabel="aktiv"
                      inactiveLabel="inaktiv"
                    />
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Human Review</dt>
                  <dd>
                    <StatusBadge
                      active={status.human_review_enabled}
                      activeLabel="aktiv"
                      inactiveLabel="inaktiv"
                    />
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Email Sending</dt>
                  <dd>
                    <Badge tone={status.email_sending_enabled ? "negative" : "positive"}>
                      {status.email_sending_enabled ? "aktiv" : "deaktiviert"}
                    </Badge>
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Automatic Contact</dt>
                  <dd>
                    <Badge tone={status.automatic_contact_enabled ? "negative" : "positive"}>
                      {status.automatic_contact_enabled ? "aktiv" : "deaktiviert"}
                    </Badge>
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Rate Limits</dt>
                  <dd>
                    <StatusBadge
                      active={status.rate_limits_enabled}
                      activeLabel="aktiv"
                      inactiveLabel="deaktiviert"
                    />
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Audit Logs</dt>
                  <dd>
                    <StatusBadge
                      active={status.audit_logs_enabled}
                      activeLabel="aktiv"
                      inactiveLabel="deaktiviert"
                    />
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

            <Card title="Letzte Blocks">
              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Do-not-contact Blocks</dt>
                  <dd className="text-slate-900">
                    {status.last_do_not_contact_block_count}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Review Blocks</dt>
                  <dd className="text-slate-900">{status.last_review_block_count}</dd>
                </div>
              </dl>
              <p className="mt-3 text-xs text-slate-500">
                Zähler seit dem letzten Neustart des Backends.
              </p>
            </Card>

            <Card title="Legal/Compliance Pack">
              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Data Retention</dt>
                  <dd>
                    <StatusBadge
                      active={status.data_retention_enabled}
                      activeLabel="aktiv"
                      inactiveLabel="deaktiviert"
                    />
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Retention Policies</dt>
                  <dd className="text-slate-900">{status.retention_policies_count}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Data Export</dt>
                  <dd>
                    <StatusBadge
                      active={status.data_export_available}
                      activeLabel="verfügbar"
                      inactiveLabel="deaktiviert"
                    />
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Data Subject Requests</dt>
                  <dd>
                    <StatusBadge
                      active={status.data_requests_enabled}
                      activeLabel="verfügbar"
                      inactiveLabel="deaktiviert"
                    />
                  </dd>
                </div>
              </dl>
              <div className="mt-3 rounded-lg border border-amber-400/25 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
                Legal Review erforderlich — dieses System ist auf eine rechtliche
                Prüfung vorbereitet, aber nicht als rechtssicher zertifiziert.
                Siehe{" "}
                <a href="/compliance/documents" className="underline hover:no-underline">
                  Compliance Documents
                </a>
                .
              </div>
            </Card>
          </>
        ) : null}
      </div>
    </RequireRole>
  );
}
