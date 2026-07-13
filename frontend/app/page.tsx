"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { LeadFinderApp } from "@/components/lead-finder/LeadFinderApp";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { StatusPill } from "@/components/ui/StatusPill";
import { WorkflowStep } from "@/components/ui/WorkflowStep";
import { ApiError, checkHealth, getOnboardingReadiness } from "@/lib/api";
import { isAdmin } from "@/lib/roles";
import type { HealthResponse, OnboardingReadinessResponse } from "@/lib/types";

const PRIMARY_LINK_CLASSES =
  "inline-flex items-center justify-center gap-2 rounded-xl bg-white px-6 py-3 text-sm font-semibold text-ink-950 shadow-premium transition-all hover:-translate-y-px hover:bg-slate-100";
const SECONDARY_LINK_CLASSES =
  "inline-flex items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/5 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-white/10";

interface WorkflowStepData {
  title: string;
  description: string;
}

const WORKFLOW_STEPS: WorkflowStepData[] = [
  {
    title: "Zielgruppe definieren",
    description: "Branche, Region und Angebot eingeben — optional ergänzt um ein ICP-Profil.",
  },
  {
    title: "Firmen finden",
    description: "Der Copilot sucht passende Kandidaten anhand deiner Zielgruppe.",
  },
  {
    title: "Website analysieren",
    description: "Öffentliche Website-Inhalte werden geprüft — Qualität, Struktur, erkennbare Probleme.",
  },
  {
    title: "Fit bewerten",
    description: "Fit-Score und Qualifikations-Level pro Kandidat, inklusive Begründung.",
  },
  {
    title: "Draft prüfen",
    description: "Personalisierter Entwurf zur menschlichen Prüfung — kein automatischer Versand.",
  },
];

type HealthState =
  | { status: "loading" }
  | { status: "loaded"; data: HealthResponse }
  | { status: "error"; message: string };

export default function HomePage() {
  const { currentUser } = useAuth();
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [readiness, setReadiness] = useState<OnboardingReadinessResponse | null>(null);

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

    getOnboardingReadiness()
      .then((data) => {
        if (!cancelled) setReadiness(data);
      })
      .catch(() => {
        // Informational only — the safety strip below falls back to the
        // standing product guarantees if the live check is unavailable.
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const checks = readiness?.checks;
  const safeModeActive = checks?.safe_mode_active ?? true;

  return (
    <RequireAuth>
      <div className="space-y-16 pb-8">
        {/* Hero — dark command-center surface */}
        <section className="hero-dark -mx-6 -mt-6 rounded-b-[2rem] px-6 pb-14 pt-12 sm:-mx-8 sm:px-8 sm:pb-16">
          <div className="relative flex flex-wrap items-center gap-2">
            <span className="eyebrow-dark">AI Sales Copilot</span>
            {health.status === "loaded" ? (
              <Badge tone={health.data.status === "ok" ? "positive" : "warning"}>
                Backend: {health.data.status === "ok" ? "Online" : "Eingeschränkt"}
              </Badge>
            ) : health.status === "error" ? (
              <Badge tone="negative">Backend nicht erreichbar</Badge>
            ) : null}
          </div>
          <h1 className="relative mt-6 max-w-3xl text-display-md font-bold text-white sm:text-display-lg">
            Finde Firmen. Analysiere Websites. Bereite Outreach vor.
          </h1>
          <p className="relative mt-5 max-w-2xl text-base text-white/70 sm:text-lg">
            Ein AI Sales Copilot für kontrollierte B2B-Kaltaquise — mit echter
            Firmensuche, Website-Analyse und Human Review.
          </p>
          <div className="relative mt-8 flex flex-wrap gap-3">
            <a href="#lead-finder" className={PRIMARY_LINK_CLASSES}>
              Lead Finder starten →
            </a>
            <a href="#letzte-runs" className={SECONDARY_LINK_CLASSES}>
              Letzte Runs ansehen
            </a>
          </div>

          {/* Safety strip, embedded in the hero */}
          <div className="relative mt-10 flex flex-wrap gap-3">
            <StatusPill
              dark
              tone={safeModeActive ? "positive" : "warning"}
              label={safeModeActive ? "Safe/Mock Mode aktiv" : "Echter Provider aktiv"}
              detail={
                safeModeActive
                  ? "Alle Provider laufen im Mock-Modus — keine echten Kosten."
                  : "Mindestens ein Provider läuft real — bewusst konfiguriert."
              }
            />
            <StatusPill
              dark
              tone="positive"
              label="Kein automatischer Versand"
              detail="Kein Send-Button, keine Massenzustellung — nie."
            />
            <StatusPill
              dark
              tone="positive"
              label="Human Review erforderlich"
              detail="„Approved“ heißt nur interne Freigabe, nie Versand."
            />
            <StatusPill
              dark
              tone="positive"
              label="Do-not-contact aktiv"
              detail="Blockiert Outreach-Vorbereitung an jeder Stelle."
            />
          </div>
        </section>

        {/* Workflow steps */}
        <section>
          <SectionHeader
            eyebrow="So funktioniert's"
            title="Fünf Schritte vom Zielkunden zum geprüften Draft"
            className="mb-6"
          />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {WORKFLOW_STEPS.map((step, index) => (
              <WorkflowStep
                key={step.title}
                index={index + 1}
                title={step.title}
                description={step.description}
              />
            ))}
          </div>
        </section>

        {/* Lead Finder, embedded prominently */}
        <section>
          <SectionHeader
            eyebrow="Lead Finder"
            title="Wen willst du finden?"
            description="Der Copilot sucht Kandidaten, analysiert deren Website, bewertet den Fit und erstellt nur prüfbare Drafts."
            className="mb-6"
          />
          <LeadFinderApp embedded />
        </section>

        <Card
          title="Weitere Werkzeuge"
          description="Fortgeschrittene und administrative Funktionen — für den täglichen Einstieg nicht nötig."
        >
          <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
            <Link href="/sales-strategy/icp" className="font-medium text-brand-600 hover:text-brand-700">
              Zielkunde (ICP) →
            </Link>
            <Link href="/sales-strategy/offers" className="font-medium text-brand-600 hover:text-brand-700">
              Angebot (Offer) →
            </Link>
            <Link href="/lead-sourcing" className="font-medium text-brand-600 hover:text-brand-700">
              Lead Sourcing →
            </Link>
            <Link href="/lead-qualification" className="font-medium text-brand-600 hover:text-brand-700">
              Lead Qualifikation →
            </Link>
            <Link href="/workflows/sales" className="font-medium text-brand-600 hover:text-brand-700">
              Einzelne Firma manuell analysieren →
            </Link>
            <Link href="/agents" className="font-medium text-brand-600 hover:text-brand-700">
              Einzel-Agenten →
            </Link>
            <Link href="/quality" className="font-medium text-brand-600 hover:text-brand-700">
              Quality Dashboard →
            </Link>
            <Link href="/compliance/status" className="font-medium text-brand-600 hover:text-brand-700">
              Compliance Status →
            </Link>
            <Link href="/onboarding" className="font-medium text-brand-600 hover:text-brand-700">
              Setup-Guide →
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
