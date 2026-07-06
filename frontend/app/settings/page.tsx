"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ApiError, API_BASE_URL, getLlmProviderStatus, testLlmProvider } from "@/lib/api";
import { isAdmin } from "@/lib/roles";
import type { LLMProviderStatus, LLMProviderTestResponse } from "@/lib/types";

type StatusState =
  | { status: "loading" }
  | { status: "loaded"; data: LLMProviderStatus }
  | { status: "error"; message: string };

function useLlmProviderStatus(): StatusState {
  const [state, setState] = useState<StatusState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });

    getLlmProviderStatus()
      .then((data) => {
        if (!cancelled) {
          setState({ status: "loaded", data });
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            status: "error",
            message: err instanceof ApiError ? err.message : "Unerwarteter Fehler.",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}

function LlmProviderStatusCard() {
  const { currentUser } = useAuth();
  const canTest = isAdmin(currentUser);
  const status = useLlmProviderStatus();

  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<LLMProviderTestResponse | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  async function handleTest() {
    setTesting(true);
    setTestError(null);
    setTestResult(null);
    try {
      // Relies entirely on the backend safety guard: if real calls are
      // disabled, the backend itself refuses to make one and returns a
      // clear, non-billable explanation instead — this button never
      // decides that on its own.
      const result = await testLlmProvider();
      setTestResult(result);
    } catch (err) {
      setTestError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setTesting(false);
    }
  }

  if (status.status === "loading") {
    return <p className="text-sm text-slate-500">Lade LLM-Provider-Status…</p>;
  }

  if (status.status === "error") {
    return <p className="text-sm text-rose-600">{status.message}</p>;
  }

  const data = status.data;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {data.mock_mode ? <Badge tone="info">Mock Mode Active</Badge> : null}
        {data.safe_mode ? <Badge tone="positive">No API Costs</Badge> : null}
        {data.real_calls_enabled ? (
          <Badge tone="warning">Real Calls Enabled</Badge>
        ) : (
          <Badge tone="neutral">Real Calls Disabled</Badge>
        )}
        {!data.anthropic_configured ? (
          <Badge tone="neutral">Anthropic Not Configured</Badge>
        ) : null}
      </div>

      <dl className="space-y-2 text-sm">
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Active Provider</dt>
          <dd className="font-mono text-slate-900">{data.active_provider}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Mock Mode</dt>
          <dd className="text-slate-900">{data.mock_mode ? "Ja" : "Nein"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Safe Mode</dt>
          <dd className="text-slate-900">{data.safe_mode ? "Ja" : "Nein"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Real Calls Enabled</dt>
          <dd className="text-slate-900">{data.real_calls_enabled ? "Ja" : "Nein"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Anthropic Configured</dt>
          <dd className="text-slate-900">{data.anthropic_configured ? "Ja" : "Nein"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Anthropic Model</dt>
          <dd className="font-mono text-slate-900">{data.anthropic_model ?? "—"}</dd>
        </div>
      </dl>

      {data.real_calls_enabled ? (
        <div className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          <strong>Achtung:</strong> Echte LLM-Aufrufe sind aktiviert. Agenten
          können API-Kosten verursachen.
        </div>
      ) : (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          Echte LLM-Aufrufe sind deaktiviert. Es entstehen keine API-Kosten
          durch Agenten-Ausführung.
        </div>
      )}

      <p className="text-sm text-slate-600">{data.message}</p>

      <div className="border-t border-slate-100 pt-4">
        {canTest ? (
          <>
            <Button onClick={handleTest} loading={testing}>
              Test LLM Provider
            </Button>
            {testResult ? (
              <div
                className={`mt-3 rounded-lg border px-3 py-2 text-sm ${
                  testResult.ok
                    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                    : "border-amber-200 bg-amber-50 text-amber-800"
                }`}
              >
                <p>
                  <strong>{testResult.provider}</strong>
                  {" — "}
                  {testResult.ok ? "erfolgreich" : "nicht ausgeführt"}
                </p>
                <p className="mt-1">{testResult.message}</p>
              </div>
            ) : null}
            {testError ? (
              <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {testError}
              </div>
            ) : null}
          </>
        ) : (
          <p className="text-sm text-slate-500">
            Nur Admin-Konten dürfen den LLM Provider testen.
          </p>
        )}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <RequireAuth>
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

        <Card
          title="LLM Provider"
          description="Live-Status aus dem Backend. Kein API Key wird hier je angezeigt, eingegeben oder gespeichert."
        >
          <LlmProviderStatusCard />
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
    </RequireAuth>
  );
}
