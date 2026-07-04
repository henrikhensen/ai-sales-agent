"use client";

import { useEffect, useState } from "react";

import { checkHealth } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";

type HealthState = "checking" | "up" | "down";

interface HeaderProps {
  onMenuClick: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const [health, setHealth] = useState<HealthState>("checking");

  useEffect(() => {
    let cancelled = false;

    checkHealth()
      .then((result) => {
        if (!cancelled) {
          setHealth(result.status === "ok" ? "up" : "down");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHealth("down");
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onMenuClick}
          className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 md:hidden"
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
        <span className="text-sm font-medium text-slate-500">
          AI Sales Agent Dashboard
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Badge tone="warning">Mock-Modus</Badge>
        <Badge
          tone={health === "up" ? "positive" : health === "down" ? "negative" : "neutral"}
        >
          Backend: {health === "checking" ? "prüfe..." : health === "up" ? "online" : "offline"}
        </Badge>
      </div>
    </header>
  );
}
