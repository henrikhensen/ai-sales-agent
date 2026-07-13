"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ApiError, getOutreachDispatchDashboard, getOutreachDispatches } from "@/lib/api";
import type { DispatchDashboardResponse, OutreachDispatch } from "@/lib/types";

const STATUS_TONE: Record<string, "positive" | "info" | "warning" | "negative" | "neutral"> = {
  pending: "info",
  blocked: "negative",
  ready: "info",
  external_draft_created: "positive",
  send_ready: "warning",
  sent_manually_confirmed: "positive",
  failed: "negative",
  cancelled: "neutral",
  archived: "neutral",
};

export default function OutreachDispatchPage() {
  const [dashboard, setDashboard] = useState<DispatchDashboardResponse | null>(null);
  const [dispatches, setDispatches] = useState<OutreachDispatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboardResponse, dispatchesResponse] = await Promise.all([
        getOutreachDispatchDashboard(),
        getOutreachDispatches(),
      ]);
      setDashboard(dashboardResponse);
      setDispatches(dispatchesResponse.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Outreach Dispatch</h1>
          <p className="mt-1 text-sm text-slate-600">
            Verarbeitet bereits genehmigte Outreach Queue Items kontrolliert als
            externe Drafts oder — nur bei expliziter Aktivierung — als manuell
            bestätigten Versand.
          </p>
        </div>

        <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
          <ul className="list-inside list-disc space-y-1">
            <li>Dispatch verarbeitet nur bereits genehmigte Queue Items.</li>
            <li>Default ist Draft-only — es wird keine E-Mail automatisch gesendet.</li>
            <li>Echter Versand ist standardmäßig deaktiviert.</li>
            <li>Versand braucht Human Review Approval, Do-not-contact-Check, Compliance Ack und Final Confirmation.</li>
            <li>Kein automatischer Massenversand, kein Batch Send.</li>
            <li>Mock Provider bleibt Standard.</li>
            <li>Die rechtliche Verantwortung für jede Aktion liegt beim Nutzer.</li>
          </ul>
        </div>

        {dashboard ? (
          <Card title="Status">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone={dashboard.enabled ? "positive" : "neutral"}>
                {dashboard.enabled ? "aktiv" : "deaktiviert"}
              </Badge>
              <Badge tone={dashboard.dispatch_mode === "manual_send" ? "warning" : "positive"}>
                Mode: {dashboard.dispatch_mode === "manual_send" ? "Manual Send" : "Draft-only"}
              </Badge>
              <Badge tone="neutral">Provider: {dashboard.provider}</Badge>
              <Badge tone={dashboard.real_send_enabled ? "negative" : "positive"}>
                {dashboard.real_send_enabled ? "Real Send AKTIVIERT" : "Real Send deaktiviert"}
              </Badge>
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600 sm:grid-cols-4">
              <p>Final Confirmation Required: {String(dashboard.require_final_confirmation)}</p>
              <p>Compliance Ack Required: {String(dashboard.require_compliance_ack)}</p>
              <p>Approved Review Required: {String(dashboard.require_approved_review)}</p>
              <p>Do-not-contact Check Required: {String(dashboard.require_do_not_contact_check)}</p>
              <p>Daily Limit: {dashboard.max_per_day}</p>
              <p>Hourly Limit: {dashboard.max_per_hour}</p>
            </dl>
            {!dashboard.real_send_enabled ? (
              <div className="mt-3 rounded-lg border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-200">
                Echte Sendung ist deaktiviert. Draft-only Mode ist aktiv.
              </div>
            ) : null}
            {dashboard.warnings.length > 0 ? (
              <div className="mt-3 rounded-lg border border-amber-400/25 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
                {dashboard.warnings.map((w) => (
                  <p key={w}>{w}</p>
                ))}
              </div>
            ) : null}
          </Card>
        ) : null}

        {dashboard ? (
          <Card title="Dashboard">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-xs text-slate-500">Pending</p>
                <p className="text-lg font-semibold text-slate-900">{dashboard.total_pending}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Blocked</p>
                <p className="text-lg font-semibold text-slate-900">{dashboard.total_blocked}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Ready</p>
                <p className="text-lg font-semibold text-slate-900">{dashboard.total_ready}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">External Draft Created</p>
                <p className="text-lg font-semibold text-slate-900">
                  {dashboard.total_external_draft_created}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Send Ready</p>
                <p className="text-lg font-semibold text-slate-900">{dashboard.total_send_ready}</p>
              </div>
              {dashboard.dispatch_mode === "manual_send" ? (
                <div>
                  <p className="text-xs text-slate-500">Manual Send (bestätigt)</p>
                  <p className="text-lg font-semibold text-slate-900">
                    {dashboard.total_sent_manually_confirmed}
                  </p>
                </div>
              ) : null}
              <div>
                <p className="text-xs text-slate-500">Failed</p>
                <p className="text-lg font-semibold text-slate-900">{dashboard.total_failed}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Cancelled</p>
                <p className="text-lg font-semibold text-slate-900">{dashboard.total_cancelled}</p>
              </div>
            </div>
          </Card>
        ) : null}

        <Card title="Dispatch Attempts">
          {loading ? (
            <p className="text-sm text-slate-500">Wird geladen…</p>
          ) : error ? (
            <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </div>
          ) : dispatches.length > 0 ? (
            <div className="space-y-2">
              {dispatches.map((dispatch) => (
                <div
                  key={dispatch.id}
                  className="rounded-lg border border-slate-200 bg-surface px-4 py-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium text-slate-900">
                        {dispatch.recipient_email ?? "(kein Empfänger bekannt)"}
                      </p>
                      <p className="text-xs text-slate-500">
                        {dispatch.provider} · {dispatch.dispatch_mode}
                      </p>
                    </div>
                    <Badge tone={STATUS_TONE[dispatch.dispatch_status] ?? "neutral"}>
                      {dispatch.dispatch_status}
                    </Badge>
                  </div>
                  {dispatch.last_error ? (
                    <p className="mt-2 text-xs text-rose-400">{dispatch.last_error}</p>
                  ) : null}
                  <a
                    href={`/outreach?queue_item_id=${encodeURIComponent(dispatch.queue_item_id)}`}
                    className="mt-2 inline-block text-xs underline hover:no-underline"
                  >
                    Queue Item öffnen
                  </a>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Noch keine Dispatch-Versuche.</p>
          )}
        </Card>
      </div>
    </RequireAuth>
  );
}
