"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import {
  ApiError,
  checkHealth,
  getLeadQualificationDashboard,
  getOnboardingReadiness,
  getOnboardingStatus,
  getOutreachDashboard,
  listCrmEmailDrafts,
  listSalesWorkflowRuns,
} from "@/lib/api";
import { isAdmin } from "@/lib/roles";
import type {
  EmailDraftRecord,
  HealthResponse,
  OnboardingReadinessResponse,
  OnboardingStatus,
  QualificationDashboardResponse,
  OutreachQueueDashboardResponse,
  WorkflowRunSummary,
} from "@/lib/types";

// -- step status helpers -----------------------------------------------------

type StepStatus = "offen" | "bereit" | "erledigt" | "blockiert";

const STEP_STATUS_TONE: Record<StepStatus, "positive" | "info" | "warning" | "negative" | "neutral"> = {
  offen: "neutral",
  bereit: "info",
  erledigt: "positive",
  blockiert: "negative",
};

const STEP_STATUS_LABEL: Record<StepStatus, string> = {
  offen: "Offen",
  bereit: "Bereit",
  erledigt: "Erledigt",
  blockiert: "Blockiert",
};

const PRIMARY_LINK_CLASSES =
  "inline-flex items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-700";
const SECONDARY_LINK_CLASSES =
  "inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50";

interface JourneyStepData {
  number: number;
  title: string;
  explanation: string;
  status: StepStatus;
  helpText?: string;
  ctaHref: string;
  ctaLabel: string;
  primary?: boolean;
}

function JourneyStep({ step }: { step: JourneyStepData }) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex h-6 w-6 flex-none items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-700">
          {step.number}
        </span>
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold text-slate-900">{step.title}</p>
            <Badge tone={STEP_STATUS_TONE[step.status]}>{STEP_STATUS_LABEL[step.status]}</Badge>
          </div>
          <p className="mt-0.5 text-xs text-slate-600">{step.explanation}</p>
          {step.helpText ? (
            <p className="mt-1 text-xs text-amber-700">{step.helpText}</p>
          ) : null}
        </div>
      </div>
      <Link
        href={step.ctaHref}
        className={`${step.primary ? PRIMARY_LINK_CLASSES : SECONDARY_LINK_CLASSES} flex-none`}
      >
        {step.ctaLabel} →
      </Link>
    </div>
  );
}

function OverviewCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <Card title={title}>
      <div className="space-y-1.5 text-sm text-slate-700">{children}</div>
    </Card>
  );
}

type HealthState =
  | { status: "loading" }
  | { status: "loaded"; data: HealthResponse }
  | { status: "error"; message: string };

export default function CommandCenterPage() {
  const { currentUser } = useAuth();
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const [readiness, setReadiness] = useState<OnboardingReadinessResponse | null>(null);
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRunSummary[]>([]);
  const [qualification, setQualification] = useState<QualificationDashboardResponse | null>(null);
  const [emailDrafts, setEmailDrafts] = useState<EmailDraftRecord[]>([]);
  const [outreach, setOutreach] = useState<OutreachQueueDashboardResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    checkHealth()
      .then((data) => {
        if (!cancelled) setHealth({ status: "loaded", data });
      })
      .catch((err) => {
        if (!cancelled) {
          setHealth({
            status: "error",
            message: err instanceof ApiError ? err.message : "Unbekannter Fehler.",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const loadAll = useCallback(async () => {
    // Every call below is informational only — the Command Center must
    // still render (and stay useful) even if one dashboard is unavailable
    // for the current role, so each is fetched independently and failures
    // are swallowed rather than blocking the whole page.
    const [
      onboardingResult,
      readinessResult,
      runsResult,
      qualificationResult,
      draftsResult,
      outreachResult,
    ] = await Promise.allSettled([
      getOnboardingStatus(),
      getOnboardingReadiness(),
      listSalesWorkflowRuns({ limit: 5 }),
      getLeadQualificationDashboard(),
      listCrmEmailDrafts(),
      getOutreachDashboard(),
    ]);

    if (onboardingResult.status === "fulfilled") setOnboarding(onboardingResult.value);
    if (readinessResult.status === "fulfilled") setReadiness(readinessResult.value);
    if (runsResult.status === "fulfilled") setWorkflowRuns(runsResult.value.items);
    if (qualificationResult.status === "fulfilled") setQualification(qualificationResult.value);
    if (draftsResult.status === "fulfilled") setEmailDrafts(draftsResult.value);
    if (outreachResult.status === "fulfilled") setOutreach(outreachResult.value);
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const checks = readiness?.checks;
  const hasSetup = Boolean(checks?.has_offer_profile && checks?.has_icp_profile);
  const safetyBlocked = Boolean(
    checks && (!checks.has_do_not_contact_enabled || !checks.has_human_review_enabled)
  );
  const safetyBlockedHelp = safetyBlocked
    ? "Do-not-contact oder Human Review ist nicht aktiv — bitte zuerst den Compliance Status prüfen, bevor weitergearbeitet wird."
    : undefined;

  const workflowCount = workflowRuns.length;
  const qualificationCount = qualification
    ? qualification.total_qualified +
      qualification.total_priority +
      qualification.total_needs_review +
      qualification.total_disqualified +
      qualification.total_blocked
    : 0;
  const draftCount = emailDrafts.length;
  const openReviewsCount = emailDrafts.filter(
    (d) => d.review_status === "needs_review" || d.review_status === "in_review"
  ).length;
  const outreachCount = outreach
    ? outreach.total_queued +
      outreach.total_ready_for_workflow +
      outreach.total_workflow_prepared +
      outreach.total_draft_created +
      outreach.total_review_pending +
      outreach.total_approved +
      outreach.total_external_draft_created
    : 0;

  const step1: JourneyStepData = {
    number: 1,
    title: "Zielkunde & Angebot prüfen",
    explanation:
      "Definiere, wen du ansprechen willst (ICP) und was du anbietest (Offer). Beides verbessert Qualifikations-Score und Draft-Qualität.",
    status: hasSetup ? "erledigt" : "offen",
    ctaHref: "/sales-strategy/icp",
    ctaLabel: "ICP & Offer einrichten",
  };
  const step2: JourneyStepData = {
    number: 2,
    title: "Firma oder Website analysieren",
    explanation:
      "Firmenname oder Website eingeben und optional Website Research aktivieren — der Sales Workflow sammelt öffentlich verfügbare Informationen.",
    status: safetyBlocked ? "blockiert" : workflowCount > 0 ? "erledigt" : "bereit",
    helpText: safetyBlockedHelp,
    ctaHref: "/workflows/sales",
    ctaLabel: "Firma analysieren",
    primary: true,
  };
  const step3: JourneyStepData = {
    number: 3,
    title: "Lead qualifizieren",
    explanation:
      "Jeder Workflow-Lauf berechnet automatisch einen Qualifikations-Score, ein Fit-Level und eine Handlungsempfehlung.",
    status: safetyBlocked
      ? "blockiert"
      : qualificationCount > 0
        ? "erledigt"
        : workflowCount > 0
          ? "bereit"
          : "offen",
    helpText: safetyBlockedHelp,
    ctaHref: "/lead-qualification",
    ctaLabel: "Qualifikation ansehen",
  };
  const step4: JourneyStepData = {
    number: 4,
    title: "Draft erstellen",
    explanation:
      "Der Sales Workflow erstellt automatisch einen personalisierten E-Mail-Entwurf — nur ein Entwurf, kein Versand.",
    status: safetyBlocked ? "blockiert" : draftCount > 0 ? "erledigt" : workflowCount > 0 ? "erledigt" : "offen",
    helpText: safetyBlockedHelp,
    ctaHref: "/crm",
    ctaLabel: "Drafts ansehen",
  };
  const step5: JourneyStepData = {
    number: 5,
    title: "Review durchführen",
    explanation:
      "Ein Mensch prüft jeden Draft und setzt den Review-Status. „Approved“ bedeutet ausschließlich interne Freigabe, nie Versand.",
    status: safetyBlocked
      ? "blockiert"
      : draftCount === 0
        ? "offen"
        : openReviewsCount > 0
          ? "bereit"
          : "erledigt",
    helpText: safetyBlockedHelp,
    ctaHref: "/reviews",
    ctaLabel: "Zur Review-Übersicht",
  };
  const step6: JourneyStepData = {
    number: 6,
    title: "In Outreach Queue vormerken — kein Versand",
    explanation:
      "Freigegebene, qualifizierte Leads werden priorisiert in einer Queue vorgemerkt. Es gibt keinen Versand-Button und keinen automatischen Versand.",
    status: safetyBlocked
      ? "blockiert"
      : outreachCount > 0
        ? "erledigt"
        : draftCount > 0
          ? "bereit"
          : "offen",
    helpText: safetyBlockedHelp,
    ctaHref: "/outreach",
    ctaLabel: "Zur Outreach Queue",
  };

  const warnings = Array.from(
    new Set([...(readiness?.blockers ?? []), ...(readiness?.warnings ?? []), ...(qualification?.warnings ?? []), ...(outreach?.warnings ?? [])])
  ).slice(0, 5);

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold text-slate-900">AI Sales Copilot — Command Center</h1>
            {health.status === "loaded" ? (
              <Badge tone={health.data.status === "ok" ? "positive" : "warning"}>
                Backend: {health.data.status === "ok" ? "Online" : "Eingeschränkt"}
              </Badge>
            ) : health.status === "error" ? (
              <Badge tone="negative">Backend nicht erreichbar</Badge>
            ) : null}
          </div>
          <p className="mt-2 max-w-3xl text-sm text-slate-600">
            Dieses Tool unterstützt dich bei Recherche, Qualifikation und
            Entwurfserstellung für Vertriebs-Outreach — als
            Entscheidungshilfe, nicht als Autopilot. Es sendet nie
            selbstständig eine E-Mail und nimmt nie automatisch Kontakt auf.
            Jeder Schritt bleibt nachvollziehbar und von einem Menschen
            geprüft.
          </p>
        </div>

        <Card title="Safety Status" className="border-emerald-200 bg-emerald-50/40">
          <div className="grid gap-2 sm:grid-cols-2">
            <div className="flex items-start gap-2">
              <Badge tone={checks?.safe_mode_active ?? true ? "positive" : "warning"}>
                {checks?.safe_mode_active ?? true ? "Safe/Mock Mode aktiv" : "Echter Provider aktiv"}
              </Badge>
              <span className="text-xs text-slate-600">
                {checks?.safe_mode_active ?? true
                  ? "Alle Provider laufen im Mock-Modus — keine echten API-Kosten, keine echte Mailbox betroffen."
                  : "Mindestens ein Provider läuft real. Prüfe die Provider-Einstellungen bewusst."}
              </span>
            </div>
            <div className="flex items-start gap-2">
              <Badge tone="positive">Kein automatischer Versand</Badge>
              <span className="text-xs text-slate-600">
                Es gibt keinen Send-Button und keine Massenzustellung — jede
                Kontaktaufnahme bleibt manuell und bewusst.
              </span>
            </div>
            <div className="flex items-start gap-2">
              <Badge tone="positive">Human Review erforderlich</Badge>
              <span className="text-xs text-slate-600">
                „Approved“ heißt ausschließlich interne Freigabe, nie Versand.
              </span>
            </div>
            <div className="flex items-start gap-2">
              <Badge tone="positive">Do-not-contact aktiv</Badge>
              <span className="text-xs text-slate-600">
                Ein Opt-out-Eintrag blockiert Outreach-Vorbereitung und
                Review-Freigabe an jeder Stelle.
              </span>
            </div>
            <div className="flex items-start gap-2 sm:col-span-2">
              <Badge tone="neutral">Echte Provider nur bewusst aktiv</Badge>
              <span className="text-xs text-slate-600">
                LLM: {checks?.real_llm_configured ? "echt aktiv" : "Mock"} · Email
                Integration: {checks?.email_integration_configured ? "echt aktiv" : "Mock"} ·
                Reply Tracking: {checks?.reply_tracking_configured ? "echt aktiv" : "Mock"}.{" "}
                <Link href="/compliance/status" className="underline hover:no-underline">
                  Details im Compliance Status →
                </Link>
              </span>
            </div>
          </div>
        </Card>

        {onboarding && !onboarding.is_completed ? (
          <Card title="Setup-Guide">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-2 rounded-full bg-brand-600 transition-all"
                      style={{ width: `${onboarding.progress_percent}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium text-slate-700">
                    {onboarding.progress_percent}%
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-600">
                  Ausführlicher Setup-Guide mit allen Einzelschritten.
                </p>
              </div>
              <Link href="/onboarding" className={SECONDARY_LINK_CLASSES}>
                Zum Setup-Guide →
              </Link>
            </div>
          </Card>
        ) : null}

        <div>
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Dein Arbeitsablauf</h2>
          <div className="grid gap-4 lg:grid-cols-3">
            <Card
              title="A · Setup"
              description="Zielkunde und Angebot definieren, Sicherheits-Status im Blick behalten."
            >
              <JourneyStep step={step1} />
            </Card>

            <Card
              title="B · Lead prüfen"
              description="Firma oder Website eingeben, automatisch recherchieren und qualifizieren lassen."
            >
              <div className="space-y-3">
                <JourneyStep step={step2} />
                <JourneyStep step={step3} />
              </div>
            </Card>

            <Card
              title="C · Draft & Review"
              description="Personalisierten Entwurf prüfen, freigeben und vormerken — kein Versand-UI."
            >
              <div className="space-y-3">
                <JourneyStep step={step4} />
                <JourneyStep step={step5} />
                <JourneyStep step={step6} />
              </div>
            </Card>
          </div>
        </div>

        <div>
          <h2 className="mb-3 text-lg font-semibold text-slate-900">Überblick</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <OverviewCard title="Letzte Workflows">
              {workflowRuns.length === 0 ? (
                <p className="text-slate-500">Noch keine Workflow-Läufe.</p>
              ) : (
                <ul className="space-y-1">
                  {workflowRuns.slice(0, 4).map((run) => (
                    <li key={run.id} className="flex items-center justify-between gap-2">
                      <span className="truncate">{run.company_name}</span>
                      <Badge tone={run.status === "completed" ? "positive" : "neutral"}>
                        {run.status}
                      </Badge>
                    </li>
                  ))}
                </ul>
              )}
              <Link
                href="/workflows/history"
                className="mt-2 inline-block text-xs font-medium text-brand-600 hover:text-brand-700"
              >
                Alle Workflows →
              </Link>
            </OverviewCard>

            <OverviewCard title="Leads mit nächstem Schritt">
              {qualification && qualificationCount > 0 ? (
                <ul className="space-y-1">
                  <li className="flex items-center justify-between">
                    <span>Priorisiert</span>
                    <Badge tone="positive">{qualification.total_priority}</Badge>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>Zur Prüfung</span>
                    <Badge tone="warning">{qualification.total_needs_review}</Badge>
                  </li>
                  <li className="flex items-center justify-between">
                    <span>Qualifiziert</span>
                    <Badge tone="info">{qualification.total_qualified}</Badge>
                  </li>
                </ul>
              ) : (
                <p className="text-slate-500">Noch keine qualifizierten Leads.</p>
              )}
              <Link
                href="/lead-qualification"
                className="mt-2 inline-block text-xs font-medium text-brand-600 hover:text-brand-700"
              >
                Zur Lead-Qualifikation →
              </Link>
            </OverviewCard>

            <OverviewCard title="Offene Reviews">
              <p className="text-2xl font-semibold text-slate-900">{openReviewsCount}</p>
              <p className="text-xs text-slate-500">
                {openReviewsCount === 0
                  ? "Kein Draft wartet aktuell auf Prüfung."
                  : "Drafts warten auf menschliche Prüfung."}
              </p>
              <Link
                href="/reviews"
                className="mt-2 inline-block text-xs font-medium text-brand-600 hover:text-brand-700"
              >
                Zur Review-Übersicht →
              </Link>
            </OverviewCard>

            <OverviewCard title="Letzte Warnings">
              {warnings.length === 0 ? (
                <p className="text-slate-500">Keine aktiven Warnings.</p>
              ) : (
                <ul className="space-y-1 text-xs text-amber-800">
                  {warnings.map((w) => (
                    <li key={w}>• {w}</li>
                  ))}
                </ul>
              )}
              <Link
                href="/compliance/status"
                className="mt-2 inline-block text-xs font-medium text-brand-600 hover:text-brand-700"
              >
                Compliance Status →
              </Link>
            </OverviewCard>
          </div>
        </div>

        <Card title="Weitere Werkzeuge" description="Fortgeschrittene und administrative Funktionen — für den täglichen Einstieg nicht nötig.">
          <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
            <Link href="/agents" className="font-medium text-brand-600 hover:text-brand-700">
              Einzel-Agenten →
            </Link>
            <Link href="/crm/pipeline" className="font-medium text-brand-600 hover:text-brand-700">
              CRM Pipeline →
            </Link>
            <Link href="/research/website" className="font-medium text-brand-600 hover:text-brand-700">
              Website Research (einzeln) →
            </Link>
            <Link href="/quality" className="font-medium text-brand-600 hover:text-brand-700">
              Quality Dashboard →
            </Link>
            <Link href="/settings" className="font-medium text-brand-600 hover:text-brand-700">
              Einstellungen →
            </Link>
            {isAdmin(currentUser) ? (
              <Link href="/admin/controls" className="font-medium text-brand-600 hover:text-brand-700">
                Admin Controls →
              </Link>
            ) : null}
          </div>
        </Card>
      </div>
    </RequireAuth>
  );
}
