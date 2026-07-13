"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ApiError, getQualityDashboard, getQualityStatus } from "@/lib/api";
import type { QualityDashboardResponse, QualityStatusResponse } from "@/lib/types";

const READINESS_TONE: Record<string, "positive" | "warning" | "negative" | "neutral"> = {
  beta_ready: "positive",
  beta_testable: "warning",
  needs_improvement: "warning",
  not_ready: "negative",
};

const SCORE_LEVEL_TONE: Record<string, "positive" | "warning" | "negative" | "neutral"> = {
  excellent: "positive",
  good: "positive",
  acceptable: "neutral",
  weak: "warning",
  poor: "negative",
  blocked: "negative",
};

function ScoreValue({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) {
    return <span className="text-slate-400">–</span>;
  }
  return <span className="font-semibold text-slate-900">{value.toFixed(1)}</span>;
}

export default function QualityDashboardPage() {
  const [status, setStatus] = useState<QualityStatusResponse | null>(null);
  const [dashboard, setDashboard] = useState<QualityDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusResult, dashboardResult] = await Promise.all([
        getQualityStatus(),
        getQualityDashboard(),
      ]);
      setStatus(statusResult);
      setDashboard(dashboardResult);
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
      deniedMessage="Nur Admin-, Sales- und Reviewer-Konten haben Zugriff auf das Quality Dashboard."
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Quality Dashboard</h1>
          <p className="mt-1 text-sm text-slate-600">
            Regelbasierte Qualitäts-Scores und Feedback im Überblick.
          </p>
        </div>

        <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
          <p className="font-medium">Wichtiger Hinweis</p>
          <ul className="mt-1 list-inside list-disc space-y-0.5">
            <li>Quality Scores sind Entscheidungshilfen, keine Garantien.</li>
            <li>
              Feedback ändert nie automatisch einen Draft oder löst einen Versand aus.
            </li>
            <li>
              &quot;Beta Ready&quot; ist ein technisches Signal, keine rechtliche
              Freigabe.
            </li>
            <li>Human Review und Do-not-contact bleiben weiterhin verpflichtend.</li>
          </ul>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Wird geladen…</p>
        ) : error ? (
          <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
            {error}
          </div>
        ) : (
          <>
            {status ? (
              <Card title="Konfiguration">
                <p className="text-sm text-slate-600">{status.message}</p>
                <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Feedback Loop</dt>
                    <dd>
                      <Badge tone={status.quality_feedback_enabled ? "positive" : "neutral"}>
                        {status.quality_feedback_enabled ? "aktiv" : "deaktiviert"}
                      </Badge>
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Scoring</dt>
                    <dd>
                      <Badge tone={status.quality_scoring_enabled ? "positive" : "neutral"}>
                        {status.quality_scoring_enabled
                          ? `aktiv (${status.quality_scoring_provider})`
                          : "deaktiviert"}
                      </Badge>
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">LLM Quality Advisor</dt>
                    <dd>
                      <Badge tone={status.quality_scoring_use_llm ? "info" : "neutral"}>
                        {status.quality_scoring_use_llm ? "aktiv" : "regelbasiert"}
                      </Badge>
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Auto-Score Workflows/Drafts</dt>
                    <dd className="text-slate-900">
                      {status.auto_score_workflows ? "Workflows " : ""}
                      {status.auto_score_drafts ? "Drafts" : ""}
                      {!status.auto_score_workflows && !status.auto_score_drafts
                        ? "deaktiviert"
                        : ""}
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Min. Draft Score</dt>
                    <dd className="text-slate-900">{status.min_draft_score}</dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Min. Lead / Workflow Score</dt>
                    <dd className="text-slate-900">
                      {status.min_lead_score} / {status.min_workflow_score}
                    </dd>
                  </div>
                </dl>
              </Card>
            ) : null}

            {dashboard ? (
              <>
                <Card title="Beta Readiness">
                  <div className="flex items-center gap-3">
                    <Badge tone={READINESS_TONE[dashboard.beta_readiness_level] ?? "neutral"}>
                      {dashboard.beta_readiness_level}
                    </Badge>
                    <p className="text-sm text-slate-600">{dashboard.message}</p>
                  </div>
                  {dashboard.warnings.length > 0 ? (
                    <ul className="mt-3 list-inside list-disc space-y-0.5 text-sm text-amber-200">
                      {dashboard.warnings.map((warning) => (
                        <li key={warning}>{warning}</li>
                      ))}
                    </ul>
                  ) : null}
                </Card>

                <Card title="Durchschnittliche Scores">
                  <dl className="grid gap-3 text-sm sm:grid-cols-3">
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Email Drafts</dt>
                      <dd>
                        <ScoreValue value={dashboard.average_draft_quality_score} />
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Leads</dt>
                      <dd>
                        <ScoreValue value={dashboard.average_lead_quality_score} />
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Workflows</dt>
                      <dd>
                        <ScoreValue value={dashboard.average_workflow_quality_score} />
                      </dd>
                    </div>
                  </dl>
                </Card>

                <Card title="Feedback">
                  <dl className="grid gap-3 text-sm sm:grid-cols-3">
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Gesamt</dt>
                      <dd className="text-slate-900">{dashboard.total_feedback_items}</dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Offen</dt>
                      <dd className="text-slate-900">{dashboard.open_feedback_items}</dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-slate-500">Blockierend</dt>
                      <dd>
                        <Badge tone={dashboard.blocking_feedback_items > 0 ? "negative" : "positive"}>
                          {dashboard.blocking_feedback_items}
                        </Badge>
                      </dd>
                    </div>
                  </dl>
                  <a
                    href="/quality/feedback"
                    className="mt-3 inline-block text-sm text-brand-700 underline hover:no-underline"
                  >
                    Feedback ansehen/verwalten
                  </a>
                </Card>

                <div className="grid gap-6 sm:grid-cols-2">
                  <Card title="Top Quality Issues">
                    {dashboard.top_quality_issues.length === 0 ? (
                      <p className="text-sm text-slate-500">Keine Daten.</p>
                    ) : (
                      <ul className="space-y-1 text-sm">
                        {dashboard.top_quality_issues.map((issue) => (
                          <li key={issue.tag} className="flex justify-between">
                            <span className="text-slate-700">{issue.tag}</span>
                            <span className="text-slate-500">{issue.count}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Card>
                  <Card title="Top Verbesserungsvorschläge">
                    {dashboard.top_improvement_suggestions.length === 0 ? (
                      <p className="text-sm text-slate-500">Keine Daten.</p>
                    ) : (
                      <ul className="space-y-1 text-sm">
                        {dashboard.top_improvement_suggestions.map((issue) => (
                          <li key={issue.tag} className="flex justify-between">
                            <span className="text-slate-700">{issue.tag}</span>
                            <span className="text-slate-500">{issue.count}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Card>
                </div>

                <div className="grid gap-6 sm:grid-cols-2">
                  <Card title="Beste Drafts">
                    {dashboard.best_performing_drafts.length === 0 ? (
                      <p className="text-sm text-slate-500">Keine Daten.</p>
                    ) : (
                      <ul className="space-y-1 text-sm">
                        {dashboard.best_performing_drafts.map((entry) => (
                          <li key={entry.entity_id} className="flex items-center justify-between">
                            <span className="truncate text-slate-700">{entry.entity_id}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-slate-900">{entry.score_total}</span>
                              <Badge tone={SCORE_LEVEL_TONE[entry.score_level] ?? "neutral"}>
                                {entry.score_level}
                              </Badge>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Card>
                  <Card title="Schwächste Drafts">
                    {dashboard.weakest_drafts.length === 0 ? (
                      <p className="text-sm text-slate-500">Keine Daten.</p>
                    ) : (
                      <ul className="space-y-1 text-sm">
                        {dashboard.weakest_drafts.map((entry) => (
                          <li key={entry.entity_id} className="flex items-center justify-between">
                            <span className="truncate text-slate-700">{entry.entity_id}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-slate-900">{entry.score_total}</span>
                              <Badge tone={SCORE_LEVEL_TONE[entry.score_level] ?? "neutral"}>
                                {entry.score_level}
                              </Badge>
                            </div>
                          </li>
                        ))}
                      </ul>
                    )}
                  </Card>
                </div>
              </>
            ) : null}
          </>
        )}
      </div>
    </RequireRole>
  );
}
