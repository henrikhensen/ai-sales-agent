import Link from "next/link";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

interface ResearchTool {
  href: string;
  name: string;
  description: string;
}

const RESEARCH_TOOLS: ResearchTool[] = [
  {
    href: "/research/website",
    name: "Website Research",
    description:
      "Ruft eine öffentlich zugängliche Website ab und extrahiert daraus lesbaren Text. Kein LLM-Call, keine KI-Kosten.",
  },
];

export default function ResearchOverviewPage() {
  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Research</h1>
          <p className="mt-1 text-sm text-slate-600">
            Analysewerkzeuge, die ausschließlich vom Nutzer angegebene,
            öffentlich zugängliche Quellen abrufen. Es wird nichts automatisch
            versendet und niemand automatisch kontaktiert.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {RESEARCH_TOOLS.map((tool) => (
            <Link key={tool.href} href={tool.href} className="block">
              <Card className="h-full transition-shadow hover:shadow-md">
                <div className="flex items-center justify-between gap-2">
                  <h2 className="text-base font-semibold text-slate-900">
                    {tool.name}
                  </h2>
                  <Badge tone="info">Research</Badge>
                </div>
                <p className="mt-2 text-sm text-slate-600">{tool.description}</p>
              </Card>
            </Link>
          ))}
        </div>
      </div>
    </RequireAuth>
  );
}
