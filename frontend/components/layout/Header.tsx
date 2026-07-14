"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { ApiError, getCorsDebug } from "@/lib/api";

// Backed by GET /api/v1/system/cors-debug — public, no database
// dependency — so this badge answers exactly one question ("can the
// browser reach and read the backend at all") without being conflated
// with database/Redis readiness (see the Settings page for that detail).
// "cors" and "down" are both connectivity failures but from
// ApiError.kind: "cors" means the backend answered a plain (non-CORS)
// reachability probe, so it must never be shown as "offline" either —
// only "down"/"not_configured" mean the backend genuinely couldn't be
// reached at all.
type HealthState = "checking" | "up" | "cors" | "down";

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

const HEALTH_DOT: Record<HealthState, string> = {
  checking: "bg-muted/30",
  up: "bg-emerald-400 motion-safe:animate-pulse-soft",
  cors: "bg-amber-400",
  down: "bg-rose-400",
};

const HEALTH_LABEL: Record<HealthState, string> = {
  checking: "prüfe …",
  up: "online",
  cors: "CORS blockiert",
  down: "offline",
};

export function Header({ onMenuClick, showMenuButton = true }: HeaderProps) {
  const [health, setHealth] = useState<HealthState>("checking");
  const { currentUser, isAuthenticated, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;

    function runCheck() {
      getCorsDebug()
        .then(() => {
          if (!cancelled) {
            setHealth("up");
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setHealth(err instanceof ApiError && err.kind === "cors" ? "cors" : "down");
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
        <div className="hidden items-center gap-2 sm:flex">
          <span className="h-1.5 w-1.5 flex-none rounded-full bg-amber-400" aria-hidden="true" />
          <span className="mono-label-invert">Mock-Modus</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`h-1.5 w-1.5 flex-none rounded-full ${HEALTH_DOT[health]}`} aria-hidden="true" />
          <span className="mono-label-invert">Backend: {HEALTH_LABEL[health]}</span>
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
