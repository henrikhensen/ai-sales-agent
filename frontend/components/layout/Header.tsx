"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
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
    <header className="flex h-16 items-center justify-between border-b border-white/10 bg-ink-950 px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-lg p-2 text-white/70 hover:bg-white/10 hover:text-white md:hidden"
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
        <div className="flex items-center gap-2">
          <span
            className="h-2 w-2 rounded-full bg-brand-400 shadow-[0_0_12px_2px_rgba(99,102,241,0.7)]"
            aria-hidden="true"
          />
          <span className="text-sm font-semibold tracking-tight text-white">
            AI Sales Copilot
          </span>
        </div>
      </div>
      <div className="flex items-center gap-2 sm:gap-3">
        <Badge tone="warning">Mock-Modus</Badge>
        <Badge
          tone={
            health === "up"
              ? "positive"
              : health === "degraded"
                ? "warning"
                : health === "down"
                  ? "negative"
                  : "neutral"
          }
        >
          Backend:{" "}
          {health === "checking"
            ? "prüfe..."
            : health === "up"
              ? "online"
              : health === "degraded"
                ? "online (eingeschränkt)"
                : "offline"}
        </Badge>
        {isAuthenticated && currentUser ? (
          <div className="flex items-center gap-2">
            <span className="hidden text-sm text-white/70 sm:inline">
              {currentUser.full_name || currentUser.email}
            </span>
            <Badge tone="info">{currentUser.role}</Badge>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-xl px-3 py-2 text-sm font-semibold text-white/70 transition-colors hover:bg-white/10 hover:text-white"
            >
              Logout
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <Link
              href="/login"
              className="text-sm font-medium text-white/80 hover:text-white"
            >
              Login
            </Link>
            <Link
              href="/register"
              className="rounded-xl bg-white px-3 py-1.5 text-sm font-semibold text-ink-950 hover:bg-slate-100"
            >
              Registrieren
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
