"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { ApiError, getCorsDebug, getLlmProviderStatus } from "@/lib/api";

// Backed by GET /api/v1/system/cors-debug — public, no database
// dependency — so this badge answers exactly one question ("can the
// browser reach and read the backend at all") without being conflated
// with database/Redis readiness (see the Settings page for that detail).
// "down" covers both a genuinely offline backend and a CORS
// misconfiguration — the Fetch API doesn't expose which of those two a
// failed request was (see lib/api.ts's `request()`), so this is reported
// as one honest state rather than guessed at. "http_error" means the
// request completed (so CORS is fine) but the response itself wasn't ok —
// carries the real status code for a specific label (401/404/5xx/...).
type HealthState =
  | { kind: "checking" }
  | { kind: "up" }
  | { kind: "down" }
  | { kind: "http_error"; status: number };

interface HeaderProps {
  onMenuClick: () => void;
  /** Hidden on routes with no Sidebar to open (e.g. the auth pages). */
  showMenuButton?: boolean;
}

// Re-checked on this interval so a transient failure (a cold-started
// backend still warming up, a momentary network blip on first load, ...)
// self-heals within a few seconds instead of leaving the badge stuck on
// "offline" forever — this component mounts once per session (it lives
// in the shared layout), so without a periodic re-check, one bad first
// request would never be retried until the user manually reloads.
const HEALTH_RECHECK_INTERVAL_MS = 15_000;

function healthDotClass(health: HealthState): string {
  switch (health.kind) {
    case "checking":
      return "bg-muted/30";
    case "up":
      return "bg-emerald-400 motion-safe:animate-pulse-soft";
    case "down":
      return "bg-rose-400";
    case "http_error":
      return "bg-amber-400";
  }
}

function healthLabel(health: HealthState): string {
  switch (health.kind) {
    case "checking":
      return "prüfe …";
    case "up":
      return "online";
    case "down":
      return "nicht erreichbar";
    case "http_error":
      if (health.status === 401) return "nicht autorisiert (401)";
      if (health.status === 404) return "Endpoint nicht gefunden (404)";
      if (health.status >= 500) return `Serverfehler (${health.status})`;
      return `Fehler (${health.status})`;
  }
}

// "mock"/"real" only ever gets set from a real, authenticated backend read
// (GET /settings/llm/status) — never assumed. Pre-login or on a failed
// fetch, the pill simply doesn't render rather than risk stating a safety
// mode that hasn't actually been confirmed.
type LlmModeState = "checking" | "mock" | "real";

const LLM_MODE_DOT: Record<LlmModeState, string> = {
  checking: "bg-muted/30",
  mock: "bg-emerald-400",
  real: "bg-amber-400",
};

const LLM_MODE_LABEL: Record<LlmModeState, string> = {
  checking: "prüfe …",
  mock: "Mock-Modus",
  real: "Echte LLM-Aufrufe aktiv",
};

export function Header({ onMenuClick, showMenuButton = true }: HeaderProps) {
  const [health, setHealth] = useState<HealthState>({ kind: "checking" });
  const [llmMode, setLlmMode] = useState<LlmModeState>("checking");
  const { currentUser, isAuthenticated, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;

    function runCheck() {
      getCorsDebug()
        .then(() => {
          if (!cancelled) {
            setHealth({ kind: "up" });
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setHealth(
              err instanceof ApiError && err.kind === "http"
                ? { kind: "http_error", status: err.status }
                : { kind: "down" }
            );
          }
        });
    }

    runCheck();
    const interval = setInterval(runCheck, HEALTH_RECHECK_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  // Only ever queried once a session exists — the endpoint requires auth,
  // and pre-login there is no session-specific mode to report.
  useEffect(() => {
    if (!isAuthenticated) {
      setLlmMode("checking");
      return;
    }
    let cancelled = false;
    getLlmProviderStatus()
      .then((data) => {
        if (!cancelled) setLlmMode(data.mock_mode ? "mock" : "real");
      })
      .catch(() => {
        // Informational badge only — a failed read must never claim a mode
        // that wasn't actually confirmed, so it just stays hidden.
      });
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <header className="flex h-14 items-center justify-between border-b border-muted/10 bg-canvas px-4 sm:px-6">
      <div className="flex items-center gap-3">
        {showMenuButton ? (
          <button
            type="button"
            onClick={onMenuClick}
            className="p-2 text-muted/70 hover:text-muted md:hidden"
            aria-label="Menü öffnen"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              className="h-5 w-5"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5M3.75 17.25h16.5" />
            </svg>
          </button>
        ) : null}
        <span className="mono-label-invert">AI Sales Copilot</span>
      </div>
      <div className="flex items-center gap-4 sm:gap-6">
        {isAuthenticated && llmMode !== "checking" ? (
          <div className="hidden items-center gap-2 sm:flex">
            <span className={`h-1.5 w-1.5 flex-none rounded-full ${LLM_MODE_DOT[llmMode]}`} aria-hidden="true" />
            <span className="mono-label-invert">{LLM_MODE_LABEL[llmMode]}</span>
          </div>
        ) : null}
        <div className="flex items-center gap-2">
          <span className={`h-1.5 w-1.5 flex-none rounded-full ${healthDotClass(health)}`} aria-hidden="true" />
          <span className="mono-label-invert">Backend: {healthLabel(health)}</span>
        </div>
        {isAuthenticated && currentUser ? (
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-muted/70 sm:inline">
              {currentUser.full_name || currentUser.email}
            </span>
            <span className="mono-label-invert">{currentUser.role}</span>
            <button
              type="button"
              onClick={handleLogout}
              className="border border-muted/20 px-3 py-1.5 text-xs font-semibold text-muted/80 transition-colors hover:border-muted hover:text-muted"
            >
              Logout
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm font-medium text-muted/80 hover:text-muted">
              Login
            </Link>
            <Link
              href="/register"
              className="border border-muted bg-muted px-3 py-1.5 text-sm font-semibold text-canvas transition-colors hover:bg-transparent hover:text-muted"
            >
              Registrieren
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
