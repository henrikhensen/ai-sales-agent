"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import {
  ApiError,
  checkHealth,
  getOnboardingReadiness,
  getOnboardingStatus,
} from "@/lib/api";
import { isAdmin } from "@/lib/roles";
import type {
  HealthResponse,
  OnboardingReadinessResponse,
  OnboardingStatus,
} from "@/lib/types";

const READINESS_TONE: Record<string, "positive" | "info" | "warning" | "negative" | "neutral"> = {
  not_ready: "negative",
  demo_ready: "warning",
  internal_ready: "info",
  beta_ready: "positive",
};

const STEP_LABELS: Record<string, string> = {
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
  completion: "Abschluss",
};

interface AgentLink {
  href: string;
  name: string;
  description: string;
}

const AGENT_LINKS: AgentLink[] = [
  {
    href: "/agents/lead-research",
    name: "Lead Research",
    description: "Erstes Lead-Profil aus Basisangaben.",
  },
  {
    href: "/agents/company-intelligence",
    name: "Company Intelligence",
    description: "Tiefere strategische Unternehmensanalyse.",
  },
  {
    href: "/agents/personalization",
    name: "Personalization",
    description: "Personalisierungsstrategie für den Vertrieb.",
  },
  {
    href: "/agents/email-draft",
    name: "Email Draft",
    description: "Menschlich zu prüfender E-Mail-Entwurf.",
  },
  {
    href: "/agents/reply-analysis",
    name: "Reply Analysis",
    description: "Klassifikation und Handlungsempfehlung für Antworten.",
  },
];

type HealthState =
  | { status: "loading" }
  | { status: "loaded"; data: HealthResponse }
  | { status: "error"; message: string };

export default function DashboardPage() {
  const { currentUser } = useAuth();
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [onboarding, setOnboarding] = useState<OnboardingStatus | null>(null);
  const [readiness, setReadiness] = useState<OnboardingReadinessResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    checkHealth()
      .then((data) => {
        if (!cancelled) {
          setHealth({ status: "loaded", data });
        }
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

  const loadOnboarding = useCallback(async () => {
    try {
      const [statusResponse, readinessResponse] = await Promise.all([
        getOnboardingStatus(),
        getOnboardingReadiness(),
      ]);
      setOnboarding(statusResponse);
      setReadiness(readinessResponse);
    } catch {
      // Onboarding widget is informational only — a failure here should
      // never block the rest of the dashboard from rendering.
    }
  }, []);

  useEffect(() => {
    loadOnboarding();
  }, [loadOnboarding]);

  return (
    <RequireAuth>
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">AI Sales Agent</h1>
        <p className="mt-1 text-sm text-slate-600">
          Dashboard für die Analyse- und Entwurfswerkzeuge des AI Sales Agent
          Systems.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card title="Backend-Status">
          {health.status === "loading" ? (
            <p className="text-sm text-slate-500">Prüfe Backend…</p>
          ) : health.status === "error" ? (
            <div className="space-y-2">
              <Badge tone="negative">Nicht erreichbar</Badge>
              <p className="text-sm text-slate-600">{health.message}</p>
            </div>
          ) : (
            <div className="space-y-2">
              <Badge tone={health.data.status === "ok" ? "positive" : "warning"}>
                {health.data.status === "ok" ? "Online" : "Eingeschränkt"}
              </Badge>
              <dl className="space-y-1 text-sm text-slate-600">
                <div className="flex justify-between">
                  <dt>Service</dt>
                  <dd>{health.data.service}</dd>
                </div>
                <div className="flex justify-between">
                  <dt>Umgebung</dt>
                  <dd>{health.data.environment}</dd>
                </div>
                {Object.entries(health.data.components).map(([name, component]) => (
                  <div key={name} className="flex justify-between capitalize">
                    <dt>{name}</dt>
                    <dd>
                      <Badge tone={component.status === "up" ? "positive" : "negative"}>
                        {component.status}
                      </Badge>
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </Card>

        <Card title="Wichtige Hinweise">
          <ul className="space-y-2 text-sm text-slate-600">
            <li className="flex items-start gap-2">
              <Badge tone="warning">Mock-Modus</Badge>
              <span>
                Standardmäßig aktiv für LLM, Email Integration und Reply
                Tracking — es entstehen keine echten API-Kosten und keine
                echte Mailbox wird berührt. Echte Provider sind optional und
                nur nach expliziter Aktivierung in <code>.env</code> aktiv.
              </span>
            </li>
            <li className="flex items-start gap-2">
              <Badge tone="info">Nur Entwürfe, kein Versand</Badge>
              <span>
                Dieses Tool erstellt E-Mail-Entwürfe (lokal und optional
                extern in Gmail/Outlook), sendet aber selbst nie eine E-Mail.
                &bdquo;Approved&ldquo; bedeutet ausschließlich interne
                Freigabe, nie Versand. Externe Drafts entstehen nur durch
                einen bewussten, manuellen Klick.
              </span>
            </li>
            <li className="flex items-start gap-2">
              <Badge tone="positive">Do-not-contact hat Vorrang</Badge>
              <span>
                Ein aktiver Opt-out-Eintrag blockiert Outreach-Vorbereitung
                und Review-Freigabe — das lässt sich an keiner Stelle
                umgehen.
              </span>
            </li>
            <li className="flex items-start gap-2">
              <Badge tone="neutral">Reply Tracking liest nur</Badge>
              <span>
                Antworten werden nur gelesen und gespeichert, nie automatisch
                beantwortet — es gibt keinen Send-Button für Antworten.
              </span>
            </li>
          </ul>
        </Card>
      </div>

      <Card title="Onboarding &amp; Setup">
        {onboarding && readiness ? (
          <div className="space-y-3">
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
              <Badge tone={READINESS_TONE[readiness.readiness_level] ?? "neutral"}>
                {readiness.readiness_level}
              </Badge>
            </div>
            <p className="text-xs text-slate-600">
              {onboarding.is_completed
                ? "Onboarding abgeschlossen."
                : onboarding.next_step
                  ? `Nächster empfohlener Schritt: ${STEP_LABELS[onboarding.next_step] ?? onboarding.next_step}`
                  : "Alle Schritte bearbeitet."}
            </p>
            <div className="flex flex-wrap gap-3 text-sm">
              <Link href="/onboarding" className="font-medium text-brand-600 hover:text-brand-700">
                Zum Onboarding →
              </Link>
              {isAdmin(currentUser) ? (
                <Link
                  href="/admin/controls"
                  className="font-medium text-brand-600 hover:text-brand-700"
                >
                  Zu Admin Controls →
                </Link>
              ) : null}
              <Link
                href="/lead-sourcing"
                className="font-medium text-brand-600 hover:text-brand-700"
              >
                Zu Lead Sourcing →
              </Link>
              <Link href="/outreach" className="font-medium text-brand-600 hover:text-brand-700">
                Zur Outreach Queue →
              </Link>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Onboarding-Status wird geladen…</p>
        )}
      </Card>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Schnellzugriff</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Link href="/lead-sourcing" className="block">
            <Card className="h-full transition-shadow hover:shadow-md">
              <p className="text-sm font-semibold text-slate-900">Lead Sourcing</p>
              <p className="mt-1 text-xs text-slate-600">Leads anhand ICP finden.</p>
            </Card>
          </Link>
          <Link href="/outreach" className="block">
            <Card className="h-full transition-shadow hover:shadow-md">
              <p className="text-sm font-semibold text-slate-900">Outreach Queue</p>
              <p className="mt-1 text-xs text-slate-600">
                Qualifizierte Leads priorisieren — kein automatischer Versand.
              </p>
            </Card>
          </Link>
          <Link href="/workflows/sales" className="block">
            <Card className="h-full transition-shadow hover:shadow-md">
              <p className="text-sm font-semibold text-slate-900">Sales Workflow</p>
              <p className="mt-1 text-xs text-slate-600">Lead-Analyse und Draft erstellen.</p>
            </Card>
          </Link>
          <Link href="/replies" className="block">
            <Card className="h-full transition-shadow hover:shadow-md">
              <p className="text-sm font-semibold text-slate-900">Reply Inbox</p>
              <p className="mt-1 text-xs text-slate-600">Antworten ansehen (nur lesen).</p>
            </Card>
          </Link>
          <Link href="/compliance/status" className="block">
            <Card className="h-full transition-shadow hover:shadow-md">
              <p className="text-sm font-semibold text-slate-900">Compliance Status</p>
              <p className="mt-1 text-xs text-slate-600">Alle Schutzmechanismen im Überblick.</p>
            </Card>
          </Link>
          <Link href="/crm/pipeline" className="block">
            <Card className="h-full transition-shadow hover:shadow-md">
              <p className="text-sm font-semibold text-slate-900">CRM Pipeline</p>
              <p className="mt-1 text-xs text-slate-600">Leads nach Status gruppiert.</p>
            </Card>
          </Link>
        </div>
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Agenten</h2>
          <Link href="/agents" className="text-sm font-medium text-brand-600 hover:text-brand-700">
            Alle Agenten ansehen →
          </Link>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {AGENT_LINKS.map((agent) => (
            <Link key={agent.href} href={agent.href} className="block">
              <Card className="h-full transition-shadow hover:shadow-md">
                <h3 className="text-sm font-semibold text-slate-900">{agent.name}</h3>
                <p className="mt-1 text-sm text-slate-600">{agent.description}</p>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </div>
    </RequireAuth>
  );
}
