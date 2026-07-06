"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import {
  ApiError,
  API_BASE_URL,
  disconnectEmailProvider,
  getEmailIntegrationProviders,
  getEmailIntegrationStatus,
  getLlmProviderStatus,
  startEmailProviderConnection,
  testLlmProvider,
} from "@/lib/api";
import { canManageEmailIntegrationConnection, isAdmin } from "@/lib/roles";
import type {
  EmailIntegrationProvider,
  EmailIntegrationProvidersResponse,
  EmailIntegrationStatus,
  LLMProviderStatus,
  LLMProviderTestResponse,
} from "@/lib/types";

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

      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
        <ul className="list-inside list-disc space-y-1">
          <li>Mock Provider ist kostenlos und sicher.</li>
          <li>Echte LLM Calls können API-Kosten verursachen.</li>
          <li>Echte LLM Calls senden Inhalte an den gewählten Provider.</li>
          <li>Es werden keine E-Mails automatisch versendet.</li>
        </ul>
      </div>

      <div className="border-t border-slate-100 pt-4">
        {canTest ? (
          <>
            <Button onClick={handleTest} loading={testing}>
              LLM Verbindung testen
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

function EmailIntegrationCard() {
  const { currentUser } = useAuth();
  const canManage = canManageEmailIntegrationConnection(currentUser);
  const searchParams = useSearchParams();

  const [status, setStatus] = useState<EmailIntegrationStatus | null>(null);
  const [providers, setProviders] = useState<EmailIntegrationProvidersResponse | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [connectingProvider, setConnectingProvider] =
    useState<EmailIntegrationProvider | null>(null);
  const [disconnectingProvider, setDisconnectingProvider] =
    useState<EmailIntegrationProvider | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusResponse, providersResponse] = await Promise.all([
        getEmailIntegrationStatus(),
        getEmailIntegrationProviders(),
      ]);
      setStatus(statusResponse);
      setProviders(providersResponse);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Reflects the outcome of an OAuth redirect back from
  // GET /integrations/email/{provider}/callback.
  const callbackProvider = searchParams.get("email_integration");
  const callbackConnected = searchParams.get("connected");

  async function handleConnect(provider: EmailIntegrationProvider) {
    setConnectingProvider(provider);
    setActionError(null);
    try {
      const result = await startEmailProviderConnection(provider);
      if (result.authorization_url.startsWith("http")) {
        window.location.href = result.authorization_url;
        return;
      }
      // Mock provider: no real redirect needed, connects immediately.
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setConnectingProvider(null);
    }
  }

  async function handleDisconnect(provider: EmailIntegrationProvider) {
    setDisconnectingProvider(provider);
    setActionError(null);
    try {
      await disconnectEmailProvider(provider);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setDisconnectingProvider(null);
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500">Lade Email-Integration-Status…</p>;
  }

  if (error || !status || !providers) {
    return <p className="text-sm text-rose-600">{error}</p>;
  }

  return (
    <div className="space-y-4">
      {callbackProvider ? (
        <div
          className={`rounded-lg border px-3 py-2 text-sm ${
            callbackConnected === "true"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-rose-200 bg-rose-50 text-rose-700"
          }`}
        >
          {callbackConnected === "true"
            ? `${callbackProvider} wurde erfolgreich verbunden.`
            : `Verbindung zu ${callbackProvider} ist fehlgeschlagen.`}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Badge tone="info">Active Provider: {status.active_provider}</Badge>
        {status.safe_mode ? (
          <Badge tone="positive">Safe Mode</Badge>
        ) : (
          <Badge tone="warning">Real Drafts Enabled</Badge>
        )}
        {status.connected ? (
          <Badge tone="positive">Connected</Badge>
        ) : (
          <Badge tone="neutral">Not Connected</Badge>
        )}
      </div>

      <dl className="space-y-2 text-sm">
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Active Provider</dt>
          <dd className="font-mono text-slate-900">{status.active_provider}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Echte Drafts aktiviert</dt>
          <dd className="text-slate-900">{status.real_drafts_enabled ? "Ja" : "Nein"}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Verbundenes Konto</dt>
          <dd className="text-slate-900">{status.external_account_email ?? "—"}</dd>
        </div>
      </dl>

      <p className="text-sm text-slate-600">{status.message}</p>

      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
        <ul className="list-inside list-disc space-y-1">
          <li>Mock Provider erstellt keine echten Gmail/Outlook Drafts.</li>
          <li>Echte Draft-Erstellung kann nur manuell ausgelöst werden.</li>
          <li>Es werden keine E-Mails automatisch gesendet.</li>
          <li>Es gibt keinen Send Button.</li>
          <li>Do-not-contact wird vor Draft-Erstellung geprüft.</li>
          <li>Approved bedeutet nicht Versand.</li>
        </ul>
      </div>

      <div className="border-t border-slate-100 pt-4">
        {canManage ? (
          <div className="space-y-3">
            {providers.items.map((item) => (
              <div
                key={item.provider}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2"
              >
                <div>
                  <p className="text-sm font-medium text-slate-900">
                    {item.display_name}
                    {item.is_active_provider ? (
                      <span className="ml-2 text-xs text-brand-600">(aktiv)</span>
                    ) : null}
                  </p>
                  <p className="text-xs text-slate-500">
                    {item.connected
                      ? `Verbunden${item.external_account_email ? ` (${item.external_account_email})` : ""}`
                      : "Nicht verbunden"}
                  </p>
                </div>
                {item.connected ? (
                  <Button
                    variant="secondary"
                    onClick={() => handleDisconnect(item.provider)}
                    loading={disconnectingProvider === item.provider}
                  >
                    Trennen
                  </Button>
                ) : (
                  <Button
                    variant="secondary"
                    onClick={() => handleConnect(item.provider)}
                    loading={connectingProvider === item.provider}
                  >
                    {item.display_name} verbinden
                  </Button>
                )}
              </div>
            ))}
            {actionError ? (
              <p className="text-xs text-rose-600">{actionError}</p>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            Nur Admin- und Sales-Konten dürfen eine Provider-Verbindung
            herstellen oder trennen.
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

        <Card
          title="Email Integration (Gmail/Outlook)"
          description="Live-Status aus dem Backend. Kein OAuth Token wird hier je angezeigt, eingegeben oder gespeichert."
        >
          <EmailIntegrationCard />
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
