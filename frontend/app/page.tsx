"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { HeroVisual } from "@/components/home/HeroVisual";
import { HomeFooter } from "@/components/home/HomeFooter";
import { ServiceGlyph, ServiceList } from "@/components/home/ServiceList";
import type { ServiceItem } from "@/components/home/ServiceList";
import { LeadFinderApp } from "@/components/lead-finder/LeadFinderApp";
import { Counter } from "@/components/ui/Counter";
import { FaqAccordion } from "@/components/ui/FaqAccordion";
import type { FaqItem } from "@/components/ui/FaqAccordion";
import { Reveal } from "@/components/ui/Reveal";
import { SafetyBlock } from "@/components/ui/SafetyBlock";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { WorkflowStep } from "@/components/ui/WorkflowStep";
import { ApiError, getCorsDebug, getLeadSourcingStatus } from "@/lib/api";
import type { ApiErrorKind } from "@/lib/api";
import type { CorsDebugResponse, LeadSourcingProviderStatus } from "@/lib/types";

const PRIMARY_LINK_CLASSES =
  "inline-flex items-center justify-center gap-2 border border-white bg-white px-7 py-3.5 text-sm font-bold uppercase tracking-wide text-canvas transition duration-150 hover:bg-transparent hover:text-white active:scale-[0.97] motion-reduce:active:scale-100";

const HEADLINE_LINES = ["Firmen finden.", "Websites analysieren.", "Outreach vorbereiten."];

interface TopicData {
  title: string;
  description: string;
}

// A genuine, ordered pipeline (each step depends on the previous one's
// output) — the index numeral on each card is honest information, not a
// decorative counter.
const WORKFLOW_SHOWCASE: TopicData[] = [
  {
    title: "Zielgruppe definieren",
    description: "Branche, Region und Angebot festlegen — optional ergänzt um ein ICP-Profil.",
  },
  {
    title: "Firmen recherchieren",
    description: "Der Copilot sucht passende Firmen anhand deiner Zielgruppe.",
  },
  {
    title: "Websites analysieren",
    description: "Öffentliche Website-Inhalte werden geprüft — Qualität, Struktur, erkennbare Probleme.",
  },
  {
    title: "Potenzial bewerten",
    description: "Fit-Score und Qualifikations-Level pro Kandidat, inklusive Begründung.",
  },
  {
    title: "Draft vorbereiten",
    description: "Personalisierter Entwurf zur menschlichen Prüfung.",
  },
  {
    title: "Human Review",
    description: "Ein Mensch prüft und entscheidet — kein automatischer Versand.",
  },
];

const FUNKTIONSBEREICHE: ServiceItem[] = [
  {
    title: "Firmensuche",
    description: "Der Copilot durchsucht öffentliche Quellen nach passenden Firmen für deine Zielgruppe.",
  },
  {
    title: "Website Research",
    description:
      "Öffentliche Website-Inhalte werden automatisch analysiert — Qualität, Struktur, erkennbare Schwächen.",
  },
  {
    title: "Lead Qualification",
    description: "Jeder Kandidat erhält einen nachvollziehbaren Fit-Score mit Begründung.",
  },
  {
    title: "Outreach Drafts",
    description: "Personalisierte Entwürfe zur Prüfung — nie ein automatischer Versand.",
  },
  {
    title: "Human Review",
    description: "Ein Mensch entscheidet über jeden einzelnen Kontakt, bevor irgendetwas passiert.",
  },
  {
    title: "Compliance",
    description: "Do-not-contact wird serverseitig erzwungen — bei jedem Workflow, ohne Ausnahme.",
  },
];

const SAFETY_ITEMS = [
  {
    label: "Kein automatischer Versand",
    detail: "Keine Nachricht verlässt das System ohne menschliche Freigabe.",
  },
  {
    label: "Kein Massenversand",
    detail: "Outreach läuft immer einzeln und geprüft — nie als Sammelaktion.",
  },
  {
    label: "Human Review bleibt Pflicht",
    detail: "„Freigegeben“ heißt nur interne Freigabe, nie Versand.",
  },
  {
    label: "Do-not-contact wird serverseitig erzwungen",
    detail: "Blockiert Outreach an jeder Stelle, unabhängig von Rolle oder Modus.",
  },
  {
    label: "Mock/Safe Mode ist Standard",
    detail: "Jeder Provider startet sicher — echte Aktionen sind nie der Default.",
  },
  {
    label: "Echte Provider nur bewusst aktivierbar",
    detail: "Zwei unabhängige, explizite Opt-ins nötig, niemals ein stiller Fallback.",
  },
];

const FAQ_ITEMS: FaqItem[] = [
  {
    question: "Was macht der AI Sales Copilot?",
    answer:
      "Er findet passende Firmen, analysiert deren Website und bereitet einen personalisierten Outreach-Entwurf vor — die Entscheidung bleibt immer bei dir.",
  },
  {
    question: "Werden Nachrichten automatisch versendet?",
    answer:
      "Nein. Es gibt keinen automatischen Versand und keine Massenzustellung — jeder Entwurf braucht eine explizite menschliche Freigabe.",
  },
  {
    question: "Woher stammen die Firmendaten?",
    answer:
      "Ausschließlich aus öffentlich zugänglichen Quellen und Websites — keine Datenkäufe, kein Scraping hinter Logins oder Paywalls.",
  },
  {
    question: "Wie funktioniert die Qualifikation?",
    answer:
      "Jeder Kandidat erhält einen Fit-Score auf Basis von Branche, Region, Website-Qualität und deinem Angebot — inklusive nachvollziehbarer Begründung.",
  },
  {
    question: "Was bedeutet Human Review?",
    answer:
      "Ein Mensch sieht sich jeden Kandidaten und jeden Entwurf an, bevor irgendetwas den Status „freigegeben“ erreicht. Freigegeben heißt nie versendet.",
  },
  {
    question: "Wie wird Do-not-contact berücksichtigt?",
    answer:
      "Jeder Workflow prüft die Do-not-contact-Liste zuerst und blockiert bei einem Treffer — unabhängig von Rolle oder Modus.",
  },
];

// Backed by GET /api/v1/system/cors-debug — public, no database
// dependency — so this badge answers exactly one question ("can the
// browser reach and read the backend at all"), same as the Header badge.
// "unreachable" covers both a genuinely offline backend and a CORS
// misconfiguration — the Fetch API doesn't expose which of those two a
// failed request was (see lib/api.ts's `request()`), so it's reported as
// one honest state rather than guessed at with a `no-cors` probe. "http"
// means the request completed (so CORS is fine) but the response itself
// wasn't ok — `httpStatus` carries the real code for a specific label.
type HealthState =
  | { status: "loading" }
  | { status: "loaded"; data: CorsDebugResponse }
  | { status: "error"; message: string; kind: ApiErrorKind; httpStatus?: number };

export default function HomePage() {
  const [health, setHealth] = useState<HealthState>({ status: "loading" });
  const [leadSourcing, setLeadSourcing] = useState<LeadSourcingProviderStatus | null>(null);

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
            httpStatus: err instanceof ApiError ? err.status : undefined,
          });
        }
      });
    // Reused from LeadFinderApp/Settings — no new fetch logic, just the
    // existing typed client call, so the trust strip's provider status is
    // always real, never guessed.
    getLeadSourcingStatus()
      .then((data) => {
        if (!cancelled) setLeadSourcing(data);
      })
      .catch(() => {
        // Informational only — a failed read simply leaves the strip's
        // provider items unconfirmed rather than claiming a false state.
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const backendOnline = health.status === "loaded";
  const healthLabel =
    health.status === "loaded"
      ? "Online"
      : health.status === "error"
        ? health.kind === "not_configured"
          ? "Nicht konfiguriert"
          : health.kind === "http"
            ? health.httpStatus === 401
              ? "Nicht autorisiert (401)"
              : health.httpStatus === 404
                ? "Endpoint nicht gefunden (404)"
                : (health.httpStatus ?? 0) >= 500
                  ? `Serverfehler (${health.httpStatus})`
                  : `Fehler (${health.httpStatus})`
            : "Nicht erreichbar"
        : "Prüfe …";
  const healthDotClass = backendOnline
    ? "bg-emerald-400 motion-safe:animate-pulse-soft"
    : health.status === "error"
      ? health.kind === "http"
        ? "bg-amber-400"
        : "bg-rose-400"
      : "bg-white/30";

  const braveActive = Boolean(
    leadSourcing && leadSourcing.provider === "brave" && leadSourcing.real_search_enabled
  );

  const trustStripItems: { label: string; active: boolean }[] = [
    { label: `Backend ${backendOnline ? "verbunden" : "nicht verbunden"}`, active: backendOnline },
    { label: `Brave Search ${braveActive ? "aktiv" : "im Safe Mode"}`, active: braveActive },
    { label: `Website Research ${leadSourcing ? "aktiv" : "wird geprüft"}`, active: Boolean(leadSourcing) },
    { label: "Draft-only", active: true },
    { label: "Human Review aktiv", active: true },
    { label: "Do-not-contact aktiv", active: true },
  ];

  return (
    <RequireAuth>
      {/* Full-bleed within the app shell's content column — cancels
          AppShell's own px/py so every section can run edge to edge
          instead of sitting in a padded card like the rest of the app. */}
      <div className="-mx-4 -mt-6 sm:-mx-6 lg:-mx-8">
        {/* Section 1 — Hero */}
        <section className="relative overflow-hidden border-b border-muted/10 bg-canvas pb-16 pt-8 text-muted sm:pb-20 sm:pt-10">
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
          <HeroVisual className="pointer-events-none absolute bottom-0 right-0 hidden h-64 w-auto text-muted/40 lg:block" />

          <div className="relative container-app">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-muted/10 pb-6">
              <span className="mono-label-invert">AI SALES COPILOT</span>
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
              Kontrollierte B2B-Akquise mit echten Firmendaten, klarer Qualifikation und
              menschlicher Prüfung.
            </p>

            <div
              className="mt-10 flex animate-fade-in-up flex-wrap items-center gap-6 sm:mt-12"
              style={{ animationDelay: "400ms" }}
            >
              <a href="#lead-finder" className={PRIMARY_LINK_CLASSES}>
                Lead Finder starten →
              </a>
              <a
                href="#workflow-showcase"
                className="text-sm font-semibold text-muted underline underline-offset-4 transition-colors hover:text-muted/70"
              >
                So funktioniert es
              </a>
            </div>

            <p
              className="mono-label-invert mt-8 animate-fade-in-up"
              style={{ animationDelay: "460ms" }}
            >
              Kein automatischer Versand · Human Review erforderlich
            </p>
          </div>
        </section>

        {/* Section 2 — Trust/status strip */}
        <section className="border-b border-muted/10 bg-canvas py-5">
          <div className="container-app flex flex-wrap gap-x-8 gap-y-3">
            {trustStripItems.map((item) => (
              <div key={item.label} className="flex items-center gap-2">
                <span
                  className={`h-1.5 w-1.5 flex-none rounded-full ${
                    item.active ? "bg-emerald-400" : "bg-muted/30"
                  }`}
                  aria-hidden="true"
                />
                <span className="mono-label-invert">{item.label}</span>
              </div>
            ))}
          </div>
        </section>

        <div className="container-app">
          <div className="space-y-24 py-20 sm:py-24">
            {/* Section 3 — Product positioning */}
            <section>
              <Reveal>
                <p className="max-w-3xl text-3xl font-bold leading-tight tracking-tight text-muted sm:text-5xl">
                  Wir verwandeln öffentliche Firmendaten in nachvollziehbare
                  Vertriebsentscheidungen.
                </p>
                <p className="mt-6 max-w-xl text-base text-muted/60">
                  Jeder Kandidat, jeder Score und jeder Entwurf ist nachvollziehbar begründet —
                  bereit für deine Prüfung, nie für einen automatischen Versand.
                </p>
                <a
                  href="#lead-finder"
                  className="mt-6 inline-block text-sm font-semibold text-muted underline underline-offset-4 hover:text-muted/70"
                >
                  Zum Lead Finder →
                </a>
              </Reveal>
            </section>

            {/* Section 4 — Workflow-Showcase */}
            <section id="workflow-showcase" className="scroll-mt-20">
              <Reveal>
                <SectionHeader
                  index="01"
                  eyebrow="So funktioniert es"
                  title="Vom Zielkunden zum geprüften Draft"
                  description="Ein Durchlauf, sechs Schritte — jeder baut auf dem Ergebnis des vorherigen auf."
                />
              </Reveal>
              <div className="mt-10 grid grid-cols-1 gap-px bg-muted/10 sm:grid-cols-2 lg:grid-cols-3">
                {WORKFLOW_SHOWCASE.map((topic, index) => (
                  <Reveal key={topic.title} delayMs={index * 70}>
                    <WorkflowStep
                      index={index + 1}
                      title={topic.title}
                      description={topic.description}
                      visual={<ServiceGlyph index={index} />}
                    />
                  </Reveal>
                ))}
              </div>
            </section>

            {/* Section 5 — Kennzahlen */}
            <section>
              <Reveal>
                <SectionHeader index="02" eyebrow="Kennzahlen" title="Prinzipien, keine Behauptungen" />
              </Reveal>
              <div className="mt-10 grid grid-cols-2 gap-8 lg:grid-cols-4">
                <Reveal delayMs={0}>
                  <Counter value={0} label="Automatische Send-Aktionen" description="Jede Nachricht braucht eine menschliche Freigabe." />
                </Reveal>
                <Reveal delayMs={70}>
                  <Counter value={100} suffix="%" label="Human Review" description="Jeder Kandidat wird von einem Menschen geprüft." />
                </Reveal>
                <Reveal delayMs={140}>
                  <Counter value={6} label="Kontrollierte Workflow-Schritte" description="Von der Zielgruppe bis zum geprüften Draft." />
                </Reveal>
                <Reveal delayMs={210}>
                  <Counter value={1} label="Zentrale Lead-Finder-Oberfläche" description="Ein Ort für Suche, Analyse und Review." />
                </Reveal>
              </div>
            </section>
          </div>
        </div>

        {/* Section 6 — Funktionsbereiche (full-bleed dark surface) */}
        <section className="border-y border-white/10 bg-surface py-20 text-white sm:py-24">
          <div className="container-app">
            <Reveal>
              <span className="mono-label-invert">Funktionsbereiche</span>
              <h2 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
                Sechs Module, ein kontrollierter Ablauf
              </h2>
            </Reveal>
            <div className="mt-10">
              <ServiceList items={FUNKTIONSBEREICHE} />
            </div>
          </div>
        </section>

        <div className="container-app">
          <div className="space-y-24 py-20 sm:py-24">
            {/* Section 7 (+ 8: results, rendered inline once a run exists) — Lead Finder */}
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

            {/* Section 9 — Safety */}
            <section>
              <Reveal>
                <SectionHeader index="04" eyebrow="Safety" title="Kontrolle bleibt beim Menschen" />
              </Reveal>
              <Reveal delayMs={100} className="mt-10">
                <SafetyBlock items={SAFETY_ITEMS} />
              </Reveal>
            </section>

            {/* Section 10 — FAQ */}
            <section>
              <Reveal>
                <SectionHeader index="05" eyebrow="FAQ" title="Häufige Fragen" />
              </Reveal>
              <Reveal delayMs={100} className="mt-10">
                <FaqAccordion items={FAQ_ITEMS} />
              </Reveal>
            </section>

            {/* Section 11 — Abschluss-CTA */}
            <section className="border border-muted/20 bg-surface px-6 py-16 text-center sm:px-12 sm:py-20">
              <Reveal>
                <h2 className="text-3xl font-black tracking-tight text-muted sm:text-5xl">
                  Bereit, passende Firmen
                  <br />
                  zu finden?
                </h2>
                <p className="mx-auto mt-5 max-w-xl text-base text-muted/60">
                  Starte einen kontrollierten Lead-Finder-Run und prüfe jedes Ergebnis selbst.
                </p>
                <a href="#lead-finder" className={`${PRIMARY_LINK_CLASSES} mt-8`}>
                  Lead Finder öffnen →
                </a>
              </Reveal>
            </section>
          </div>
        </div>

        {/* Section 12 — Footer */}
        <HomeFooter />
      </div>
    </RequireAuth>
  );
}
