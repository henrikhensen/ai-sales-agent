import type { ReactNode } from "react";

interface AgentFormLayoutProps {
  title: string;
  description: string;
  complianceNote?: string;
  form: ReactNode;
  result: ReactNode;
}

export function AgentFormLayout({
  title,
  description,
  complianceNote,
  form,
  result,
}: AgentFormLayoutProps) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        <p className="mt-1 text-sm text-slate-600">{description}</p>
      </div>

      <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
        <p>
          <strong>Mock-Modus aktiv:</strong> Solange{" "}
          <code className="rounded bg-amber-400/15 px-1 py-0.5">LLM_PROVIDER=mock</code>{" "}
          gesetzt ist, erzeugt dieser Agent keine echte KI-Analyse — die Antwort
          dient nur der Verifikation der Pipeline. Es entstehen keine API-Kosten.
        </p>
        {complianceNote ? <p className="mt-2">{complianceNote}</p> : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div>{form}</div>
        <div>{result}</div>
      </div>
    </div>
  );
}
