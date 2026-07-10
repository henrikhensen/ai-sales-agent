"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  ApiError,
  completeOnboarding,
  completeOnboardingStep,
  getOnboardingReadiness,
  getOnboardingStatus,
  skipOnboardingStep,
} from "@/lib/api";
import { canManageOwnOnboarding } from "@/lib/roles";
import type {
  OnboardingReadinessResponse,
  OnboardingStatus,
  OnboardingStep,
} from "@/lib/types";

const STEP_LABELS: Record<OnboardingStep, string> = {
  welcome: "Willkommen",
  profile_setup: "Profil einrichten",
  company_setup: "Unternehmen einrichten",
  offer_setup: "Offer Profile anlegen",
  icp_setup: "ICP Profile anlegen",
  safe_mode_review: "Safe Mode prüfen",
  provider_settings_review: "Provider-Einstellungen prüfen",
  compliance_review: "Compliance prüfen",
  do_not_contact_review: "Do-not-contact prüfen",
  first_lead_sourcing: "Erste Lead Sourcing Campaign",
  first_qualification: "Erste Lead Qualification",
  first_outreach_queue: "Erste Outreach Queue",
  first_draft_review: "Ersten Draft reviewen",
  first_real_world_test: "Real-World Test Mode ausprobieren",
  feedback_quality_review: "Feedback & Quality Dashboard prüfen",
  completion: "Abschluss",
};

const STEP_LINKS: Partial<Record<OnboardingStep, string>> = {
  offer_setup: "/sales-strategy/offers",
  icp_setup: "/sales-strategy/icp",
  safe_mode_review: "/settings",
  provider_settings_review: "/admin/controls",
  compliance_review: "/compliance/status",
  do_not_contact_review: "/compliance/do-not-contact",
  first_lead_sourcing: "/lead-sourcing",
  first_qualification: "/lead-qualification",
  first_outreach_queue: "/outreach",
  first_draft_review: "/reviews",
  first_real_world_test: "/real-world-test",
  feedback_quality_review: "/quality/feedback",
};

const STEP_ORDER: OnboardingStep[] = [
  "welcome",
  "profile_setup",
  "company_setup",
  "offer_setup",
  "icp_setup",
  "safe_mode_review",
  "provider_settings_review",
  "compliance_review",
  "do_not_contact_review",
  "first_lead_sourcing",
  "first_qualification",
  "first_outreach_queue",
  "first_draft_review",
  "first_real_world_test",
  "feedback_quality_review",
  "completion",
];

const READINESS_TONE: Record<string, "positive" | "info" | "warning" | "negative" | "neutral"> = {
  not_ready: "negative",
  demo_ready: "warning",
  internal_ready: "info",
  beta_ready: "positive",
};

export default function OnboardingPage() {
  const { currentUser } = useAuth();
  const canManage = canManageOwnOnboarding(currentUser);

  const [status, setStatus] = useState<OnboardingStatus | null>(null);
  const [readiness, setReadiness] = useState<OnboardingReadinessResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyStep, setBusyStep] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusResponse, readinessResponse] = await Promise.all([
        getOnboardingStatus(),
        getOnboardingReadiness(),
      ]);
      setStatus(statusResponse);
      setReadiness(readinessResponse);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  async function handleComplete(step: OnboardingStep) {
    setActionError(null);
    setBusyStep(step);
    try {
      const result = await completeOnboardingStep(step);
      setStatus(result.status);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusyStep(null);
    }
  }

  async function handleSkip(step: OnboardingStep) {
    setActionError(null);
    setBusyStep(step);
    try {
      const result = await skipOnboardingStep(step);
      setStatus(result.status);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusyStep(null);
    }
  }

  async function handleCompleteOnboarding() {
    setActionError(null);
    try {
      const result = await completeOnboarding();
      setStatus(result.status);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            Willkommen beim AI Sales Agent
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Dieser Setup-Guide führt Schritt für Schritt durch die Einrichtung:
            zuerst Offer und ICP definieren, dann Leads sourcen, qualifizieren,
            eine Outreach Queue bauen, Drafts vorbereiten und reviewen, einen
            Real-World Test Mode Lauf ausprobieren und abschließend Feedback
            geben bzw. das Quality Dashboard prüfen — und erst nach jedem
            Review-Schritt optional einen externen Draft erstellen.
          </p>
        </div>

        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <ul className="list-inside list-disc space-y-1">
            <li>Onboarding aktiviert keine echten Provider automatisch.</li>
            <li>Onboarding sendet keine E-Mails.</li>
            <li>Onboarding erstellt keine externen Drafts automatisch.</li>
            <li>Echte Sendung ist standardmäßig deaktiviert.</li>
            <li>Do-not-contact und Human Review sind Pflicht und nicht abschaltbar.</li>
            <li>
              Echte Provider (LLM, E-Mail-Integration, Reply Tracking) werden nur nach
              bewusster, expliziter Aktivierung genutzt.
            </li>
            <li>
              Quality Scores und „Beta Ready" sind Entscheidungshilfen — keine
              rechtliche Garantie oder Freigabe.
            </li>
            <li>Personenbezogene Daten sparsam verwenden — nur was für den jeweiligen Schritt nötig ist.</li>
          </ul>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Wird geladen…</p>
        ) : error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        ) : (
          <>
            {status ? (
              <Card title="Fortschritt">
                <div className="flex items-center gap-3">
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-brand-600 transition-all"
                      style={{ width: `${status.progress_percent}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-slate-700">
                    {status.progress_percent}%
                  </span>
                </div>
                <p className="mt-2 text-xs text-slate-500">
                  {status.is_completed
                    ? "Onboarding abgeschlossen."
                    : status.next_step
                      ? `Nächster empfohlener Schritt: ${STEP_LABELS[status.next_step as OnboardingStep]}`
                      : "Alle Schritte bearbeitet."}
                </p>
                {!status.is_completed && canManage ? (
                  <div className="mt-3">
                    <Button variant="secondary" onClick={handleCompleteOnboarding}>
                      Onboarding abschließen
                    </Button>
                  </div>
                ) : null}
                {actionError ? (
                  <p className="mt-2 text-sm text-rose-600">{actionError}</p>
                ) : null}
              </Card>
            ) : null}

            {readiness ? (
              <Card title="Readiness Level">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={READINESS_TONE[readiness.readiness_level] ?? "neutral"}>
                    {readiness.readiness_level}
                  </Badge>
                </div>
                <p className="mt-2 text-xs text-slate-600">{readiness.message}</p>
                {readiness.blockers.length > 0 ? (
                  <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
                    <p className="font-semibold">Blockers</p>
                    {readiness.blockers.map((b) => (
                      <p key={b}>• {b}</p>
                    ))}
                  </div>
                ) : null}
                {readiness.warnings.length > 0 ? (
                  <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                    <p className="font-semibold">Warnings</p>
                    {readiness.warnings.map((w) => (
                      <p key={w}>• {w}</p>
                    ))}
                  </div>
                ) : null}
                {readiness.recommendations.length > 0 ? (
                  <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
                    <p className="font-semibold">Recommendations</p>
                    {readiness.recommendations.map((r) => (
                      <p key={r}>• {r}</p>
                    ))}
                  </div>
                ) : null}
                <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Quality Feedback Loop</dt>
                    <dd>
                      <Badge tone={readiness.checks.beta_feedback_loop_available ? "positive" : "neutral"}>
                        {readiness.checks.beta_feedback_loop_available ? "verfügbar" : "deaktiviert"}
                      </Badge>
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Blocking Feedback respektiert</dt>
                    <dd>
                      <Badge tone={readiness.checks.blocking_feedback_respected ? "positive" : "negative"}>
                        {readiness.checks.blocking_feedback_respected ? "ja" : "nein"}
                      </Badge>
                    </dd>
                  </div>
                  <div className="flex justify-between gap-4">
                    <dt className="text-slate-500">Quality Beta Readiness</dt>
                    <dd className="text-slate-900">{readiness.checks.quality_beta_readiness_level}</dd>
                  </div>
                </dl>
              </Card>
            ) : null}

            <Card title="Setup-Schritte">
              <div className="space-y-2">
                {STEP_ORDER.map((step) => {
                  const isCompleted = status?.completed_steps.includes(step);
                  const isSkipped = status?.skipped_steps.includes(step);
                  const isCurrent = status?.current_step === step;
                  const link = STEP_LINKS[step];
                  return (
                    <div
                      key={step}
                      className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 ${
                        isCurrent ? "border-brand-400 bg-brand-50" : "border-slate-200"
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-slate-900">
                          {STEP_LABELS[step]}
                        </span>
                        {isCompleted ? <Badge tone="positive">erledigt</Badge> : null}
                        {isSkipped ? <Badge tone="neutral">übersprungen</Badge> : null}
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {link ? (
                          <a href={link} className="text-xs underline hover:no-underline">
                            Zur Seite
                          </a>
                        ) : null}
                        {canManage && !isCompleted ? (
                          <Button
                            variant="secondary"
                            loading={busyStep === step}
                            onClick={() => handleComplete(step)}
                          >
                            Als erledigt markieren
                          </Button>
                        ) : null}
                        {canManage && !isCompleted && !isSkipped ? (
                          <Button
                            variant="ghost"
                            loading={busyStep === step}
                            onClick={() => handleSkip(step)}
                          >
                            Überspringen
                          </Button>
                        ) : null}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>
          </>
        )}
      </div>
    </RequireAuth>
  );
}
