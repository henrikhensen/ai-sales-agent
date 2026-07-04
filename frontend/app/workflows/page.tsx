import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

interface WorkflowSummary {
  href: string;
  name: string;
  description: string;
}

const WORKFLOWS: WorkflowSummary[] = [
  {
    href: "/workflows/sales",
    name: "Sales Workflow",
    description:
      "Kombiniert Lead Research, Company Intelligence, Personalization und Email Draft zu einem einzigen Ablauf mit abschließender Human-Review-Zusammenfassung.",
  },
];

export default function WorkflowsOverviewPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Workflows</h1>
        <p className="mt-1 text-sm text-slate-600">
          Workflows verketten mehrere Agenten zu einem Ablauf. Sie sind wie die
          einzelnen Agenten reine Analyse- und Entwurfswerkzeuge: Es wird
          nichts automatisch versendet, niemand automatisch kontaktiert und
          kein Termin automatisch gebucht. Menschliche Prüfung bleibt für
          jede Aktion Pflicht.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {WORKFLOWS.map((workflow) => (
          <Link key={workflow.href} href={workflow.href} className="block">
            <Card className="h-full transition-shadow hover:shadow-md">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-base font-semibold text-slate-900">
                  {workflow.name}
                </h2>
                <Badge tone="info">Workflow</Badge>
              </div>
              <p className="mt-2 text-sm text-slate-600">
                {workflow.description}
              </p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
