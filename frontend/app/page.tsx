"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { LeadFinderApp } from "@/components/lead-finder/LeadFinderApp";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ApiError, checkHealth, getOnboardingReadiness } from "@/lib/api";
import { isAdmin } from "@/lib/roles";
import type { HealthResponse, OnboardingReadinessResponse } from "@/lib/types";

const PRIMARY_LINK_CLASSES =
  "inline-flex items-center justify-center gap-2 rounded-xl bg-brand-600 px-6 py-3 text-sm font-semibold text-white shadow-sm shadow-brand-600/20 transition-all hover:bg-brand-700 hover:shadow-md";
const SECONDARY_LINK_CLASSES =
  "inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50";

interface WorkflowStep {
  number: string;
  title: string;
  description: string;
}

const WORKFLOW_STEPS: WorkflowStep[] = [
  {
    number: "01",
    title: "Zielgruppe definieren",
    description: "Branche, Region und Angebot eingeben — optional ergänzt um ein ICP-Profil.",
  },
  {
    number: "02",
    title: "Firmen finden",
    description: "Der Copilot sucht passende Kandidaten anhand deiner Zielgruppe.",
  },
  {
    number: "03",
    title: "Website analysieren",
    description: "Öffentliche Website-Inhalte werden geprüft — Qualität, Struktur, erkennbare Probleme.",
  },
  {
    number: "04",
    title: "Lead bewerten",
    description: "Fit-Score und Qualifikations-Level pro Kandidat, inklusive Begründung.",
  },
  {
    number: "05",
    title: "Draft prüfen",
    description: "Personalisierter Entwurf zur menschlichen Prüfung — kein automatischer Versand.",
  },
];

type HealthState =
  | { status: "loading" }
  | { status: "loaded"; data: HealthResponse }
  | { status: "error"; message: string };

function SafetyPill({ label, detail }: { label: string; detail: string }) {
  return (
    <div className="flex flex-1 min-w-[220px] items-start gap-3 rounded-2xl border border-emerald-200 bg-emerald-50/60 px-4 py-3">
      <span className="mt-0.5 h-2 w-2 flex-none rounded-full bg-emerald-500" aria-hidden="true" />
      <div>
        <p className="text-sm font-semibold text-emerald-900">{label}</p>
        <p className="text-xs text-emerald-800">{detail}</p>
      </div>
    </div>
  );
}

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
        {/* Hero */}
        <section className="hero-surface -mx-6 -mt-6 rounded-b-3xl px-6 pb-12 pt-10 sm:-mx-8 sm:px-8">
          <div className="flex flex-wrap items-center gap-2">
            <span className="eyebrow">AI Sales Copilot</span>
            {health.status === "loaded" ? (
              <Badge tone={health.data.status === "ok" ? "positive" : "warning"}>
                Backend: {health.data.status === "ok" ? "Online" : "Eingeschränkt"}
              </Badge>
            ) : health.status === "error" ? (
              <Badge tone="negative">Backend nicht erreichbar</Badge>
            ) : null}
          </div>
          <h1 className="mt-5 max-w-3xl text-4xl font-bold leading-tight tracking-tight text-slate-900 sm:text-5xl">
            Finde passende B2B-Leads. Analysiere Websites. Erstelle geprüfte
            Outreach-Drafts.
          </h1>
          <p className="mt-5 max-w-2xl text-base text-slate-600 sm:text-lg">
            Der Copilot recherchiert, qualifiziert und bereitet Entwürfe vor —
            als Entscheidungshilfe für dein Vertriebsteam. Es erfolgt{" "}
            <strong className="font-semibold text-slate-800">
              kein automatischer Versand
            </strong>{" "}
            — jede Kontaktaufnahme bleibt eine bewusste, menschliche Entscheidung.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href="#lead-finder" className={PRIMARY_LINK_CLASSES}>
              Lead Finder starten →
            </a>
            <a href="#letzte-runs" className={SECONDARY_LINK_CLASSES}>
              Letzte Analysen ansehen
            </a>
          </div>
        </section>

        {/* Safety strip */}
        <section className="flex flex-wrap gap-3">
          <SafetyPill
            label={safeModeActive ? "Safe/Mock Mode aktiv" : "Echter Provider aktiv"}
            detail={
              safeModeActive
                ? "Alle Provider laufen im Mock-Modus — keine echten Kosten."
                : "Mindestens ein Provider läuft real — bewusst konfiguriert."
            }
          />
          <SafetyPill
            label="Kein automatischer Versand"
            detail="Kein Send-Button, keine Massenzustellung — nie."
          />
          <SafetyPill
            label="Human Review erforderlich"
            detail="„Approved“ heißt nur interne Freigabe, nie Versand."
          />
          <SafetyPill
            label="Do-not-contact aktiv"
            detail="Blockiert Outreach-Vorbereitung an jeder Stelle."
          />
        </section>

        {/* Workflow steps */}
        <section>
          <div className="mb-6 max-w-2xl">
            <span className="eyebrow">So funktioniert's</span>
            <h2 className="mt-3 text-2xl font-bold tracking-tight text-slate-900">
              Fünf Schritte vom Zielkunden zum geprüften Draft
            </h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            {WORKFLOW_STEPS.map((step) => (
              <Card key={step.number} className="flex flex-col gap-2">
                <span className="text-sm font-bold text-brand-500">{step.number}</span>
                <p className="text-sm font-semibold text-slate-900">{step.title}</p>
                <p className="text-xs text-slate-600">{step.description}</p>
              </Card>
            ))}
          </div>
        </section>

        {/* Lead Finder, embedded prominently */}
        <section>
          <div className="mb-6 max-w-2xl">
            <span className="eyebrow">Lead Finder</span>
            <h2 className="mt-3 text-2xl font-bold tracking-tight text-slate-900">
              Wen willst du finden?
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Der Copilot sucht Kandidaten, analysiert deren Website, bewertet den
              Fit und erstellt nur prüfbare Drafts.
            </p>
          </div>
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
