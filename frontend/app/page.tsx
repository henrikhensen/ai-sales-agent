"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { LeadFinderApp } from "@/components/lead-finder/LeadFinderApp";
import { SafetyBlock } from "@/components/ui/SafetyBlock";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { WorkflowStep } from "@/components/ui/WorkflowStep";
import { ApiError, checkHealth } from "@/lib/api";
import { isAdmin } from "@/lib/roles";
import type { HealthResponse } from "@/lib/types";

const PRIMARY_LINK_CLASSES =
  "inline-flex items-center justify-center gap-2 border border-white bg-white px-7 py-3.5 text-sm font-bold uppercase tracking-wide text-ink-950 transition duration-150 hover:bg-transparent hover:text-white active:scale-[0.97] motion-reduce:active:scale-100";

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

type HealthState =
  | { status: "loading" }
  | { status: "loaded"; data: HealthResponse }
  | { status: "error"; message: string };

export default function HomePage() {
  const { currentUser } = useAuth();
  const [health, setHealth] = useState<HealthState>({ status: "loading" });

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

  const healthLabel =
    health.status === "loaded"
      ? health.data.status === "ok"
        ? "Online"
        : "Eingeschränkt"
      : health.status === "error"
        ? "Nicht erreichbar"
        : "Prüfe …";
  const healthDotClass =
    health.status === "loaded"
      ? health.data.status === "ok"
        ? "bg-emerald-400 motion-safe:animate-pulse-soft"
        : "bg-amber-400"
      : health.status === "error"
        ? "bg-rose-400"
        : "bg-white/30";

  return (
    <RequireAuth>
      {/* Full-bleed within the app shell's content column — cancels
          AppShell's own px/py so the hero and safety block can run edge
          to edge instead of sitting in a padded card like the rest of
          the app. */}
      <div className="-mx-4 -mt-6 sm:-mx-6 lg:-mx-8">
        {/* Section 1 — Hero */}
        <section className="border-b border-white/10 bg-ink-950 px-4 pb-16 pt-8 text-white sm:px-6 sm:pb-20 sm:pt-10 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-6">
            <span className="mono-label-invert">AI Sales Copilot</span>
            <div className="flex items-center gap-2">
              <span className={`h-1.5 w-1.5 flex-none rounded-full ${healthDotClass}`} aria-hidden="true" />
              <span className="mono-label-invert">Backend: {healthLabel}</span>
            </div>
          </div>

          <h1 className="mt-10 font-black text-display uppercase text-white sm:mt-14">
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
            className="mt-8 max-w-xl animate-fade-in-up text-lg text-white/70 sm:mt-10"
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
              className="text-sm font-semibold text-white underline underline-offset-4 transition-colors hover:text-white/70"
            >
              Letzte Runs ansehen
            </a>
          </div>
        </section>

        <div className="px-4 sm:px-6 lg:px-8">
          <div className="space-y-24 py-20 sm:py-24">
            {/* Section 2 — Core Workflow */}
            <section>
              <SectionHeader
                index="02"
                eyebrow="Core Workflow"
                title="Vom Zielkunden zum geprüften Draft"
                description="Ein Durchlauf, fünf Schritte — jeder baut auf dem Ergebnis des vorherigen auf."
              />
              <div className="mt-10 grid grid-cols-1 gap-px bg-ink-950/10 sm:grid-cols-2 lg:grid-cols-5">
                {CORE_WORKFLOW.map((topic, index) => (
                  <div
                    key={topic.title}
                    className="animate-fade-in-up"
                    style={{ animationDelay: `${index * 70}ms` }}
                  >
                    <WorkflowStep index={index + 1} title={topic.title} description={topic.description} />
                  </div>
                ))}
              </div>
            </section>

            {/* Section 3 (+ 4: results, rendered inline once a run exists) — Lead Finder */}
            <section id="lead-finder" className="scroll-mt-20">
              <SectionHeader
                index="03"
                eyebrow="Lead Finder"
                title="Wen willst du finden?"
                description="Der Copilot sucht Kandidaten, analysiert deren Website, bewertet den Fit und erstellt nur prüfbare Drafts."
              />
              <div className="mt-10">
                <LeadFinderApp embedded />
              </div>
            </section>

            {/* Section 5 — Safety */}
            <section>
              <SectionHeader index="04" eyebrow="Safety" title="Kontrolle bleibt beim Menschen" />
              <div className="mt-10 animate-fade-in-up">
                <SafetyBlock items={SAFETY_ITEMS} />
              </div>
            </section>

            {/* Secondary tools — a plain list, not another card grid */}
            <section className="border-t border-ink-950/10 pt-10">
              <p className="mono-label">Weitere Werkzeuge</p>
              <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm">
                <Link href="/sales-strategy/icp" className="font-medium text-ink-700 hover:text-ink-950">
                  Zielkunde (ICP) →
                </Link>
                <Link href="/sales-strategy/offers" className="font-medium text-ink-700 hover:text-ink-950">
                  Angebot (Offer) →
                </Link>
                <Link href="/lead-sourcing" className="font-medium text-ink-700 hover:text-ink-950">
                  Lead Sourcing →
                </Link>
                <Link href="/lead-qualification" className="font-medium text-ink-700 hover:text-ink-950">
                  Lead Qualifikation →
                </Link>
                <Link href="/workflows/sales" className="font-medium text-ink-700 hover:text-ink-950">
                  Einzelne Firma manuell analysieren →
                </Link>
                <Link href="/agents" className="font-medium text-ink-700 hover:text-ink-950">
                  Einzel-Agenten →
                </Link>
                <Link href="/quality" className="font-medium text-ink-700 hover:text-ink-950">
                  Quality Dashboard →
                </Link>
                <Link href="/compliance/status" className="font-medium text-ink-700 hover:text-ink-950">
                  Compliance Status →
                </Link>
                <Link href="/onboarding" className="font-medium text-ink-700 hover:text-ink-950">
                  Setup-Guide →
                </Link>
                {isAdmin(currentUser) ? (
                  <Link href="/admin/controls" className="font-medium text-ink-700 hover:text-ink-950">
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
