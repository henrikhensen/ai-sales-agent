"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { LeadFinderApp } from "@/components/lead-finder/LeadFinderApp";
import { Reveal } from "@/components/ui/Reveal";
import { SafetyBlock } from "@/components/ui/SafetyBlock";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { WorkflowStep } from "@/components/ui/WorkflowStep";
import { ApiError, getCorsDebug } from "@/lib/api";
import type { ApiErrorKind } from "@/lib/api";
import { isAdmin } from "@/lib/roles";
import type { CorsDebugResponse } from "@/lib/types";

const PRIMARY_LINK_CLASSES =
  "inline-flex items-center justify-center gap-2 border border-white bg-white px-7 py-3.5 text-sm font-bold uppercase tracking-wide text-canvas transition duration-150 hover:bg-transparent hover:text-white active:scale-[0.97] motion-reduce:active:scale-100";

const HEADLINE_LINES = ["Find companies.", "Analyze websites.", "Prepare outreach."];

interface TopicData {
  title: string;
  description: string;
}

// A genuine, ordered pipeline (each step depends on the previous one's
// output) — the index numeral on each card is honest information, not a
// decorative counter.
const CORE_WORKFLOW: TopicData[] = [
  {
    title: "Zielgruppe",
    description: "Branche, Region und Angebot definieren — optional ergänzt um ein ICP-Profil.",
  },
  {
    title: "Firmensuche",
    description: "Der Copilot sucht passende Kandidaten anhand deiner Zielgruppe.",
  },
  {
    title: "Website-Analyse",
    description: "Öffentliche Website-Inhalte werden geprüft — Qualität, Struktur, erkennbare Probleme.",
  },
  {
    title: "Qualification",
    description: "Fit-Score und Qualifikations-Level pro Kandidat, inklusive Begründung.",
  },
  {
    title: "Review Draft",
    description: "Personalisierter Entwurf zur menschlichen Prüfung — kein automatischer Versand.",
  },
];

const SAFETY_ITEMS = [
  {
    label: "Kein Auto-Send",
    detail: "Kein Send-Button, keine Massenzustellung — nie.",
  },
  {
    label: "Human Review Pflicht",
    detail: "„Approved“ heißt nur interne Freigabe, nie Versand.",
  },
  {
    label: "Do-not-contact aktiv",
    detail: "Blockiert Outreach-Vorbereitung an jeder Stelle.",
  },
];

// Backed by GET /api/v1/system/cors-debug — public, no database
// dependency — so this badge answers exactly one question ("can the
// browser reach and read the backend at all"), same as the Header badge.
type HealthState =
  | { status: "loading" }
  | { status: "loaded"; data: CorsDebugResponse }
  | { status: "error"; message: string; kind: ApiErrorKind };

export default function HomePage() {
  const { currentUser } = useAuth();
  const [health, setHealth] = useState<HealthState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    getCorsDebug()
      .then((data) => {
        if (!cancelled) setHealth({ status: "loaded", data });
      })
      .catch((err) => {
        if (!cancelled) {
          setHealth({
            status: "error",
            message: err instanceof ApiError ? err.message : "Unbekannter Fehler.",
            kind: err instanceof ApiError ? err.kind : "unreachable",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const healthLabel =
    health.status === "loaded"
      ? "Online"
      : health.status === "error"
        ? health.kind === "cors"
          ? "CORS blockiert"
          : health.kind === "not_configured"
            ? "Nicht konfiguriert"
            : "Nicht erreichbar"
        : "Prüfe …";
  const healthDotClass =
    health.status === "loaded"
      ? "bg-emerald-400 motion-safe:animate-pulse-soft"
      : health.status === "error"
        ? health.kind === "cors"
          ? "bg-amber-400"
          : "bg-rose-400"
        : "bg-white/30";

  return (
    <RequireAuth>
      {/* Full-bleed within the app shell's content column — cancels
          AppShell's own px/py so the hero and safety block can run edge
          to edge instead of sitting in a padded card like the rest of
          the app. */}
      <div className="-mx-4 -mt-6 sm:-mx-6 lg:-mx-8">
        {/* Section 1 — Hero */}
        <section className="relative overflow-hidden border-b border-muted/10 bg-canvas px-4 pb-16 pt-8 text-muted sm:px-6 sm:pb-20 sm:pt-10 lg:px-8">
          {/* Dezente, sich langsam bewegende Hintergrundflächen — reine
              CSS-Formen aus der Markenpalette, kein Fremdbild. Bleiben
              unter `prefers-reduced-motion` stehen (globale Regel in
              globals.css erzwingt eine Iteration statt Endlosschleife). */}
          <div
            className="pointer-events-none absolute -left-24 -top-24 h-[26rem] w-[26rem] rounded-full bg-surface opacity-60 blur-3xl motion-safe:animate-drift-a"
            aria-hidden="true"
          />
          <div
            className="pointer-events-none absolute -bottom-32 -right-16 h-[30rem] w-[30rem] rounded-full bg-muted/10 blur-3xl motion-safe:animate-drift-b"
            aria-hidden="true"
          />

          <div className="relative">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-muted/10 pb-6">
              <span className="mono-label-invert">AI Sales Copilot</span>
              <div className="flex items-center gap-2">
                <span className={`h-1.5 w-1.5 flex-none rounded-full ${healthDotClass}`} aria-hidden="true" />
                <span className="mono-label-invert">Backend: {healthLabel}</span>
              </div>
            </div>

            <h1 className="mt-10 font-black text-display uppercase text-muted sm:mt-14">
              {HEADLINE_LINES.map((line, index) => (
                <span
                  key={line}
                  className="block animate-fade-in-up"
                  style={{ animationDelay: `${index * 90}ms` }}
                >
                  {line}
                </span>
              ))}
            </h1>

            <p
              className="mt-8 max-w-xl animate-fade-in-up text-lg text-muted/70 sm:mt-10"
              style={{ animationDelay: "320ms" }}
            >
              Ein AI Sales Copilot für kontrollierte B2B-Kaltaquise — mit echter
              Firmensuche, Website-Analyse und Human Review.
            </p>

            <div
              className="mt-10 flex animate-fade-in-up flex-wrap items-center gap-6 sm:mt-12"
              style={{ animationDelay: "400ms" }}
            >
              <a href="#lead-finder" className={PRIMARY_LINK_CLASSES}>
                Lead Finder starten →
              </a>
              <a
                href="#letzte-runs"
                className="text-sm font-semibold text-muted underline underline-offset-4 transition-colors hover:text-muted/70"
              >
                Letzte Runs ansehen
              </a>
            </div>
          </div>
        </section>

        <div className="px-4 sm:px-6 lg:px-8">
          <div className="space-y-24 py-20 sm:py-24">
            {/* Section 2 — Core Workflow */}
            <section>
              <Reveal>
                <SectionHeader
                  index="02"
                  eyebrow="Core Workflow"
                  title="Vom Zielkunden zum geprüften Draft"
                  description="Ein Durchlauf, fünf Schritte — jeder baut auf dem Ergebnis des vorherigen auf."
                />
              </Reveal>
              <div className="mt-10 grid grid-cols-1 gap-px bg-muted/10 sm:grid-cols-2 lg:grid-cols-5">
                {CORE_WORKFLOW.map((topic, index) => (
                  <Reveal key={topic.title} delayMs={index * 70}>
                    <WorkflowStep index={index + 1} title={topic.title} description={topic.description} />
                  </Reveal>
                ))}
              </div>
            </section>

            {/* Section 3 (+ 4: results, rendered inline once a run exists) — Lead Finder */}
            <section id="lead-finder" className="scroll-mt-20">
              <Reveal>
                <SectionHeader
                  index="03"
                  eyebrow="Lead Finder"
                  title="Wen willst du finden?"
                  description="Der Copilot sucht Kandidaten, analysiert deren Website, bewertet den Fit und erstellt nur prüfbare Drafts."
                />
              </Reveal>
              <div className="mt-10">
                <LeadFinderApp embedded />
              </div>
            </section>

            {/* Section 5 — Safety */}
            <section>
              <Reveal>
                <SectionHeader index="04" eyebrow="Safety" title="Kontrolle bleibt beim Menschen" />
              </Reveal>
              <Reveal delayMs={100} className="mt-10">
                <SafetyBlock items={SAFETY_ITEMS} />
              </Reveal>
            </section>

            {/* Secondary tools — a plain list, not another card grid */}
            <section className="border-t border-muted/15 pt-10">
              <p className="mono-label">Weitere Werkzeuge</p>
              <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm">
                <Link href="/sales-strategy/icp" className="font-medium text-muted/70 hover:text-muted">
                  Zielkunde (ICP) →
                </Link>
                <Link href="/sales-strategy/offers" className="font-medium text-muted/70 hover:text-muted">
                  Angebot (Offer) →
                </Link>
                <Link href="/lead-sourcing" className="font-medium text-muted/70 hover:text-muted">
                  Lead Sourcing →
                </Link>
                <Link href="/lead-qualification" className="font-medium text-muted/70 hover:text-muted">
                  Lead Qualifikation →
                </Link>
                <Link href="/workflows/sales" className="font-medium text-muted/70 hover:text-muted">
                  Einzelne Firma manuell analysieren →
                </Link>
                <Link href="/agents" className="font-medium text-muted/70 hover:text-muted">
                  Einzel-Agenten →
                </Link>
                <Link href="/quality" className="font-medium text-muted/70 hover:text-muted">
                  Quality Dashboard →
                </Link>
                <Link href="/compliance/status" className="font-medium text-muted/70 hover:text-muted">
                  Compliance Status →
                </Link>
                <Link href="/onboarding" className="font-medium text-muted/70 hover:text-muted">
                  Setup-Guide →
                </Link>
                {isAdmin(currentUser) ? (
                  <Link href="/admin/controls" className="font-medium text-muted/70 hover:text-muted">
                    Admin Controls →
                  </Link>
                ) : null}
              </div>
            </section>
          </div>
        </div>
      </div>
    </RequireAuth>
  );
}
