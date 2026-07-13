"use client";

import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { StatusPill } from "@/components/ui/StatusPill";
import {
  ApiError,
  API_BASE_URL,
  checkHealth,
  disconnectEmailProvider,
  getEmailIntegrationProviders,
  getEmailIntegrationStatus,
  getLeadSourcingStatus,
  getLlmProviderStatus,
  getOutreachDispatchDashboard,
  startEmailProviderConnection,
  testLlmProvider,
} from "@/lib/api";
import { canManageEmailIntegrationConnection, isAdmin } from "@/lib/roles";
import type {
  DispatchDashboardResponse,
  EmailIntegrationProvider,
  EmailIntegrationProvidersResponse,
  EmailIntegrationStatus,
  HealthResponse,
  LeadSourcingProviderStatus,
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

const SOURCING_PROVIDER_LABEL: Record<string, string> = {
  mock: "Mock",
  brave: "Brave Search",
  search_api: "Such-API",
  manual: "Manuell",
};

function LeadSourcingStatusCard() {
  const [status, setStatus] = useState<
    | { state: "loading" }
    | { state: "loaded"; data: LeadSourcingProviderStatus }
    | { state: "error"; message: string }
  >({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    getLeadSourcingStatus()
      .then((data) => {
        if (!cancelled) setStatus({ state: "loaded", data });
      })
      .catch((err) => {
        if (!cancelled) {
          setStatus({
            state: "error",
            message: err instanceof ApiError ? err.message : "Unerwarteter Fehler.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (status.state === "loading") {
    return <p className="text-sm text-slate-500">Lade Lead-Sourcing-Status…</p>;
  }
  if (status.state === "error") {
    return <p className="text-sm text-rose-600">{status.message}</p>;
  }

  const data = status.data;
  const providerLabel = SOURCING_PROVIDER_LABEL[data.provider] ?? data.provider;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Badge tone={data.real_search_enabled ? "warning" : "positive"}>
          {providerLabel} {data.real_search_enabled ? "· echte Suche aktiv" : "· Safe Mode"}
        </Badge>
      </div>
      <dl className="space-y-2 text-sm">
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Aktiver Provider</dt>
          <dd className="font-mono text-slate-900">{data.provider}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-slate-500">Echte Suche aktiviert</dt>
          <dd className="text-slate-900">{data.real_search_enabled ? "Ja" : "Nein"}</dd>
        </div>
      </dl>
      {data.warnings.length > 0 ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          {data.warnings.map((w) => (
            <p key={w}>• {w}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function SafetyStatusCard() {
  const llmStatus = useLlmProviderStatus();
  const llmModeLabel =
    llmStatus.status === "loaded"
      ? llmStatus.data.mock_mode
        ? "Mock"
        : "Real"
      : llmStatus.status === "error"
        ? "Unbekannt"
        : "Lädt…";
  const llmModeTone =
    llmStatus.status === "loaded" ? (llmStatus.data.mock_mode ? "positive" : "warning") : "neutral";

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <StatusPill
        tone="positive"
        label="Kein automatischer Versand"
        detail="Kein Send-Button, keine Massenzustellung — nie."
      />
      <StatusPill
        tone="positive"
        label="Human Review erforderlich"
        detail="„Approved“ heißt nur interne Freigabe, nie Versand."
      />
      <StatusPill
        tone="positive"
        label="Do-not-contact aktiv"
        detail="Blockiert Outreach-Vorbereitung an jeder Stelle."
      />
      <StatusPill
        tone={llmModeTone}
        label={`LLM Modus: ${llmModeLabel}`}
        detail={
          llmModeLabel === "Mock"
            ? "Keine echten LLM-Kosten, keine echten Prompt-Inhalte versendet."
            : llmModeLabel === "Real"
              ? "Echte LLM-Aufrufe sind bewusst aktiviert."
              : "Status wird geladen oder ist aktuell nicht abrufbar."
        }
      />
    </div>
  );
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

function OutreachDispatchStatusCard() {
  const [dashboard, setDashboard] = useState<DispatchDashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getOutreachDispatchDashboard()
      .then((data) => {
        if (!cancelled) setDashboard(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return <p className="text-sm text-rose-600">{error}</p>;
  }
  if (!dashboard) {
    return <p className="text-sm text-slate-500">Wird geladen…</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={dashboard.enabled ? "positive" : "neutral"}>
          {dashboard.enabled ? "aktiv" : "deaktiviert"}
        </Badge>
        <Badge tone={dashboard.dispatch_mode === "manual_send" ? "warning" : "positive"}>
          Mode: {dashboard.dispatch_mode === "manual_send" ? "Manual Send" : "Draft-only"}
        </Badge>
        <Badge tone="neutral">Provider: {dashboard.provider}</Badge>
        <Badge tone={dashboard.real_send_enabled ? "negative" : "positive"}>
          {dashboard.real_send_enabled ? "Real Send aktiviert" : "Real Send deaktiviert"}
        </Badge>
      </div>
      <dl className="grid grid-cols-2 gap-2 text-xs text-slate-600 sm:grid-cols-2">
        <p>Final Confirmation Required: {String(dashboard.require_final_confirmation)}</p>
        <p>Compliance Ack Required: {String(dashboard.require_compliance_ack)}</p>
        <p>Approved Review Required: {String(dashboard.require_approved_review)}</p>
        <p>Do-not-contact Check Required: {String(dashboard.require_do_not_contact_check)}</p>
        <p>Daily Limit: {dashboard.max_per_day}</p>
        <p>Hourly Limit: {dashboard.max_per_hour}</p>
      </dl>
      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
        <ul className="list-inside list-disc space-y-1">
          <li>Draft-only ist der sichere Standard.</li>
          <li>Real Send ist standardmäßig deaktiviert.</li>
          <li>Echte Sendung erfordert explizite Aktivierung.</li>
          <li>Do-not-contact und Human Review können nicht umgangen werden.</li>
        </ul>
      </div>
    </div>
  );
}

// Raw diagnostic view of what the frontend actually resolved and what the
// backend actually answered — no secrets in either response (health/lead
// sourcing status never return one). Helps tell apart "wrong URL", "CORS
// blocked", and "backend genuinely down/degraded" without opening devtools.
function BackendDiagnostics() {
  const healthEndpoint = `${API_BASE_URL}/api/v1/health`;
  const [health, setHealth] = useState<
    { state: "loading" } | { state: "loaded"; data: HealthResponse } | { state: "error"; message: string }
  >({ state: "loading" });
  const [leadSourcing, setLeadSourcing] = useState<
    | { state: "loading" }
    | { state: "loaded"; data: LeadSourcingProviderStatus }
    | { state: "error"; message: string }
  >({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    checkHealth()
      .then((data) => {
        if (!cancelled) setHealth({ state: "loaded", data });
      })
      .catch((err) => {
        if (!cancelled) {
          setHealth({
            state: "error",
            message: err instanceof ApiError ? err.message : "Fetch fehlgeschlagen.",
          });
        }
      });
    getLeadSourcingStatus()
      .then((data) => {
        if (!cancelled) setLeadSourcing({ state: "loaded", data });
      })
      .catch((err) => {
        if (!cancelled) {
          setLeadSourcing({
            state: "error",
            message: err instanceof ApiError ? err.message : "Fetch fehlgeschlagen.",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <details className="mt-4 border-t border-slate-200 pt-3">
      <summary className="cursor-pointer list-none text-xs font-medium uppercase tracking-wide text-slate-400 hover:text-slate-600">
        Debug (rohe API-Antworten anzeigen)
      </summary>
      <div className="mt-3 space-y-1 text-xs">
        <p className="text-slate-500">
          Health-Endpoint: <code className="font-mono text-slate-700">{healthEndpoint}</code>
        </p>
        <p className="text-slate-500">
          Health-Response:{" "}
          <code className="font-mono text-slate-700">
            {health.state === "loading"
              ? "lädt…"
              : health.state === "error"
                ? `Fetch fehlgeschlagen: ${health.message}`
                : JSON.stringify(health.data)}
          </code>
        </p>
        <p className="text-slate-500">
          Lead-Sourcing-Provider-Status:{" "}
          <code className="font-mono text-slate-700">
            {leadSourcing.state === "loading"
              ? "lädt…"
              : leadSourcing.state === "error"
                ? `Fetch fehlgeschlagen: ${leadSourcing.message}`
                : JSON.stringify(leadSourcing.data)}
          </code>
        </p>
      </div>
    </details>
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

        <div className="grid gap-6 lg:grid-cols-2">
          <Card title="Backend">
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">API Base URL</dt>
                <dd className="font-mono text-slate-900">{API_BASE_URL}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Gesteuert über</dt>
                <dd className="text-slate-700">
                  <code>NEXT_PUBLIC_API_BASE_URL</code>
                </dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-slate-500">
              Diese URL muss vom Browser aus erreichbar sein (z. B.{" "}
              <code>http://localhost:8000</code>), nicht ein interner
              Docker-Hostname.
            </p>
            <BackendDiagnostics />
          </Card>

          <Card
            title="Lead Sourcing"
            description="Live-Status der Firmensuche. Kein API Key wird hier je angezeigt."
          >
            <LeadSourcingStatusCard />
          </Card>

          <Card
            title="LLM"
            description="Live-Status aus dem Backend. Kein API Key wird hier je angezeigt, eingegeben oder gespeichert."
          >
            <LlmProviderStatusCard />
          </Card>

          <Card
            title="Safety"
            description="Standing-Garantien dieses Systems — gelten unabhängig von Provider-Konfiguration."
          >
            <SafetyStatusCard />
          </Card>
        </div>

        <Card
          title="Email Integration (Gmail/Outlook)"
          description="Live-Status aus dem Backend. Kein OAuth Token wird hier je angezeigt, eingegeben oder gespeichert."
        >
          <EmailIntegrationCard />
        </Card>

        <Card
          title="Controlled Outreach Dispatch"
          description="Live-Status aus dem Backend. Kein Token wird hier je angezeigt, eingegeben oder gespeichert."
        >
          <OutreachDispatchStatusCard />
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
