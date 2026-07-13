"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { RequireRole } from "@/components/auth/RequireRole";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import {
  ApiError,
  completeBetaTestSession,
  createBetaTestSession,
  getBetaTestDashboard,
  getBetaTestSessions,
  startBetaTestSession,
} from "@/lib/api";
import { canManageBetaTestSessions, canViewBetaTestDashboard } from "@/lib/roles";
import type { BetaTestDashboardResponse, BetaTestSession } from "@/lib/types";

const STATUS_TONE: Record<string, "positive" | "warning" | "negative" | "neutral"> = {
  planned: "neutral",
  running: "warning",
  completed: "positive",
  cancelled: "negative",
};

const READINESS_TONE: Record<string, "positive" | "warning" | "negative" | "neutral"> = {
  beta_ready: "positive",
  beta_testable: "warning",
  needs_improvement: "warning",
  not_ready: "negative",
};

export default function BetaTestPage() {
  const { currentUser } = useAuth();
  const [sessions, setSessions] = useState<BetaTestSession[]>([]);
  const [dashboard, setDashboard] = useState<BetaTestDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [form, setForm] = useState({ name: "", description: "", target_goal: "" });
  const [creating, setCreating] = useState(false);

  const canManage = canManageBetaTestSessions(currentUser);
  const canViewDashboard = canViewBetaTestDashboard(currentUser);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const requests: [Promise<{ items: BetaTestSession[] }>, Promise<BetaTestDashboardResponse> | null] = [
        getBetaTestSessions({ limit: 100 }),
        canViewDashboard ? getBetaTestDashboard() : null,
      ];
      const [sessionsResult, dashboardResult] = await Promise.all([
        requests[0],
        requests[1] ?? Promise.resolve(null),
      ]);
      setSessions(sessionsResult.items);
      setDashboard(dashboardResult);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, [canViewDashboard]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setCreating(true);
    setActionError(null);
    try {
      await createBetaTestSession({
        name: form.name,
        description: form.description || null,
        target_goal: form.target_goal || null,
      });
      setForm({ name: "", description: "", target_goal: "" });
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setCreating(false);
    }
  }

  async function handleStart(sessionId: string) {
    setBusyId(sessionId);
    setActionError(null);
    try {
      await startBetaTestSession(sessionId);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleComplete(sessionId: string) {
    setBusyId(sessionId);
    setActionError(null);
    try {
      await completeBetaTestSession(sessionId);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <RequireRole
      allowedRoles={["admin", "sales", "reviewer"]}
      deniedMessage="Nur Admin-, Sales- und Reviewer-Konten haben Zugriff auf Beta Test Sessions."
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Beta Test Sessions</h1>
          <p className="mt-1 text-sm text-slate-600">
            Strukturiertes Tracking manueller Testrunden. Eine Session aktiviert nie
            einen echten Provider, versendet nie eine E-Mail und erstellt nie
            automatisch einen externen Draft.
          </p>
        </div>

        {actionError ? (
          <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
            {actionError}
          </div>
        ) : null}

        {canManage ? (
          <Card title="Neue Session erstellen">
            <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleCreate}>
              <Input
                label="Name"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
              <Input
                label="Zielsetzung"
                value={form.target_goal}
                onChange={(e) => setForm({ ...form, target_goal: e.target.value })}
              />
              <div className="sm:col-span-2">
                <Textarea
                  label="Beschreibung"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
              <div className="sm:col-span-2">
                <Button type="submit" loading={creating}>
                  Session erstellen
                </Button>
              </div>
            </form>
          </Card>
        ) : null}

        {canViewDashboard && dashboard ? (
          <Card title="Beta Dashboard">
            <div className="flex items-center gap-3">
              <Badge tone={READINESS_TONE[dashboard.readiness_level] ?? "neutral"}>
                {dashboard.readiness_level}
              </Badge>
              <p className="text-sm text-slate-600">{dashboard.message}</p>
            </div>
            <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Sessions</dt>
                <dd className="text-slate-900">{dashboard.sessions_count}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Laufend / Abgeschlossen</dt>
                <dd className="text-slate-900">
                  {dashboard.running_sessions_count} / {dashboard.completed_sessions_count}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Ø Quality Score</dt>
                <dd className="text-slate-900">
                  {dashboard.average_quality_score?.toFixed(1) ?? "–"}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Feedback (offen/blockierend)</dt>
                <dd className="text-slate-900">
                  {dashboard.open_feedback_items} / {dashboard.blocking_feedback_items}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Bugs gemeldet</dt>
                <dd className="text-slate-900">{dashboard.total_bugs}</dd>
              </div>
            </dl>
            {dashboard.recommendations.length > 0 ? (
              <ul className="mt-3 list-inside list-disc space-y-0.5 text-sm text-slate-700">
                {dashboard.recommendations.map((rec) => (
                  <li key={rec}>{rec}</li>
                ))}
              </ul>
            ) : null}
            {dashboard.warnings.length > 0 ? (
              <ul className="mt-3 list-inside list-disc space-y-0.5 text-sm text-amber-200">
                {dashboard.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : null}
          </Card>
        ) : null}

        {loading ? (
          <p className="text-sm text-slate-500">Wird geladen…</p>
        ) : error ? (
          <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
            {error}
          </div>
        ) : (
          <Card title="Sessions">
            <div className="space-y-2">
              {sessions.length === 0 ? (
                <p className="text-sm text-slate-500">Noch keine Sessions.</p>
              ) : null}
              {sessions.map((session) => (
                <div key={session.id} className="rounded-lg border border-slate-200 px-3 py-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-sm font-semibold text-slate-900">
                      {session.name}
                    </span>
                    <Badge tone={STATUS_TONE[session.status] ?? "neutral"}>
                      {session.status}
                    </Badge>
                  </div>
                  {session.description ? (
                    <p className="mt-1 text-sm text-slate-600">{session.description}</p>
                  ) : null}
                  <p className="mt-1 text-xs text-slate-500">
                    Workflows getestet: {session.total_workflows_tested} · Drafts geprüft:{" "}
                    {session.total_drafts_reviewed} · Feedback: {session.total_feedback_items} ·
                    Blocker: {session.blockers_count} · Bugs: {session.bugs_count}
                    {session.average_quality_score !== null &&
                    session.average_quality_score !== undefined
                      ? ` · Ø Score: ${session.average_quality_score.toFixed(1)}`
                      : ""}
                  </p>
                  {canManage ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {session.status === "planned" ? (
                        <Button
                          variant="secondary"
                          loading={busyId === session.id}
                          onClick={() => handleStart(session.id)}
                        >
                          Starten
                        </Button>
                      ) : null}
                      {session.status === "running" ? (
                        <Button
                          variant="secondary"
                          loading={busyId === session.id}
                          onClick={() => handleComplete(session.id)}
                        >
                          Abschließen
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </RequireRole>
  );
}
