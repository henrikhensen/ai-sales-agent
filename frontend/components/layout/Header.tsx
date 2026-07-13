"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { checkHealth } from "@/lib/api";

// "degraded" means the fetch succeeded and the backend responded — e.g.
// the database is up but Redis (optional, see DEPLOYMENT_RAILWAY.md) is
// not configured — so it must never be shown as "offline". Only an
// actual failed fetch (network error, CORS block, unreachable host)
// means the backend is truly offline.
type HealthState = "checking" | "up" | "degraded" | "down";

interface HeaderProps {
  onMenuClick: () => void;
}

// Re-checked on this interval so a transient failure (a cold-started
// backend still warming up, a momentary network blip on first load, ...)
// self-heals within a few seconds instead of leaving the badge stuck on
// "offline" forever — this component mounts once per session (it lives
// in the shared layout), so without a periodic re-check, one bad first
// request would never be retried until the user manually reloads.
const HEALTH_RECHECK_INTERVAL_MS = 15_000;

const HEALTH_DOT: Record<HealthState, string> = {
  checking: "bg-white/30",
  up: "bg-emerald-400",
  degraded: "bg-amber-400",
  down: "bg-rose-400",
};

const HEALTH_LABEL: Record<HealthState, string> = {
  checking: "prüfe …",
  up: "online",
  degraded: "eingeschränkt",
  down: "offline",
};

export function Header({ onMenuClick }: HeaderProps) {
  const [health, setHealth] = useState<HealthState>("checking");
  const { currentUser, isAuthenticated, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;

    function runCheck() {
      checkHealth()
        .then((result) => {
          if (!cancelled) {
            setHealth(result.status === "ok" ? "up" : "degraded");
          }
        })
        .catch(() => {
          if (!cancelled) {
            setHealth("down");
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
    <header className="flex h-14 items-center justify-between border-b border-white/10 bg-ink-950 px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="p-2 text-white/70 hover:text-white md:hidden"
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
            <span className="hidden text-sm text-white/70 sm:inline">
              {currentUser.full_name || currentUser.email}
            </span>
            <span className="mono-label-invert">{currentUser.role}</span>
            <button
              type="button"
              onClick={handleLogout}
              className="border border-white/20 px-3 py-1.5 text-xs font-semibold text-white/80 transition-colors hover:border-white hover:text-white"
            >
              Logout
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <Link href="/login" className="text-sm font-medium text-white/80 hover:text-white">
              Login
            </Link>
            <Link
              href="/register"
              className="border border-white bg-white px-3 py-1.5 text-sm font-semibold text-ink-950 hover:bg-transparent hover:text-white"
            >
              Registrieren
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
