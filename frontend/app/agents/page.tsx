import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

interface AgentSummary {
  href: string;
  name: string;
  description: string;
  kind: "Analyse" | "Strategie" | "Entwurf";
}

const AGENTS: AgentSummary[] = [
  {
    href: "/agents/lead-research",
    name: "Lead Research Agent",
    description:
      "Erstellt aus Basisangaben ein erstes Lead-Profil mit Zielkunden, Pain Points und Sales-Angles.",
    kind: "Analyse",
  },
  {
    href: "/agents/company-intelligence",
    name: "Company Intelligence Agent",
    description:
      "Tiefere strategische Unternehmensanalyse: Positionierung, Buyer Personas, Value Proposition.",
    kind: "Analyse",
  },
  {
    href: "/agents/personalization",
    name: "Personalization Engine",
    description:
      "Strukturierte Personalisierungsstrategie aus Unternehmens-, Lead- und Analyseinformationen.",
    kind: "Strategie",
  },
  {
    href: "/agents/email-draft",
    name: "Email Draft Agent",
    description:
      "Erstellt einen menschlich zu prüfenden E-Mail-Entwurf. Sendet niemals automatisch.",
    kind: "Entwurf",
  },
  {
    href: "/agents/reply-analysis",
    name: "Reply Analysis Agent",
    description:
      "Klassifiziert Lead-Antworten und empfiehlt die nächste, menschlich freizugebende Aktion.",
    kind: "Analyse",
  },
];

const KIND_TONE: Record<AgentSummary["kind"], "info" | "positive" | "warning"> = {
  Analyse: "info",
  Strategie: "positive",
  Entwurf: "warning",
};

export default function AgentsOverviewPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Agenten</h1>
        <p className="mt-1 text-sm text-slate-600">
          Alle Agenten sind Analyse- oder Entwurfswerkzeuge. Keiner von ihnen
          nimmt automatisch Kontakt auf, sendet E-Mails oder bucht Termine —
          jede Aktion bleibt ein separater, menschlich freizugebender Schritt.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {AGENTS.map((agent) => (
          <Link key={agent.href} href={agent.href} className="block">
            <Card className="h-full transition-shadow hover:shadow-md">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-base font-semibold text-slate-900">
                  {agent.name}
                </h2>
                <Badge tone={KIND_TONE[agent.kind]}>{agent.kind}</Badge>
              </div>
              <p className="mt-2 text-sm text-slate-600">{agent.description}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
