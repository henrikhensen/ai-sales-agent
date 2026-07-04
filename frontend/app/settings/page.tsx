"use client";

import { Card } from "@/components/ui/Card";
import { API_BASE_URL } from "@/lib/api";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Einstellungen</h1>
        <p className="mt-1 text-sm text-slate-600">
          Konfiguration dieses Dashboards. Änderungen am LLM-Provider oder an
          Secrets erfolgen ausschließlich über die Backend-Konfiguration
          (<code>.env</code>), niemals im Frontend.
        </p>
      </div>

      <Card title="Backend-Verbindung">
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-slate-500">API Base URL</dt>
            <dd className="font-mono text-slate-900">{API_BASE_URL}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-slate-500">Gesteuert über</dt>
            <dd className="text-slate-700">
              Umgebungsvariable <code>NEXT_PUBLIC_API_BASE_URL</code>
            </dd>
          </div>
        </dl>
        <p className="mt-3 text-xs text-slate-500">
          Diese URL muss vom Browser aus erreichbar sein (z. B.{" "}
          <code>http://localhost:8000</code>), nicht ein interner
          Docker-Hostname.
        </p>
      </Card>

      <Card title="LLM Provider">
        <p className="text-sm text-slate-600">
          Der Standard-Provider ist <code>mock</code> — es entstehen keine
          echten API-Kosten und keine echte KI-Analyse wird erzeugt. Um einen
          echten Provider zu verwenden, muss serverseitig{" "}
          <code>LLM_PROVIDER=anthropic</code> sowie ein gültiger API-Key in der
          Backend-<code>.env</code>-Datei gesetzt werden. API-Keys werden
          niemals im Frontend gespeichert oder angezeigt.
        </p>
      </Card>

      <Card title="Weitere Ressourcen">
        <ul className="space-y-1 text-sm">
          <li>
            <a
              className="text-brand-600 hover:text-brand-700"
              href={`${API_BASE_URL}/docs`}
              target="_blank"
              rel="noreferrer"
            >
              Swagger / OpenAPI-Dokumentation →
            </a>
          </li>
          <li>
            <a
              className="text-brand-600 hover:text-brand-700"
              href={`${API_BASE_URL}/api/v1/health`}
              target="_blank"
              rel="noreferrer"
            >
              Health-Check-Endpoint →
            </a>
          </li>
        </ul>
      </Card>
    </div>
  );
}
