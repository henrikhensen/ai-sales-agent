"use client";

import Link from "next/link";

import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";

interface AccessDeniedProps {
  message?: string;
}

/**
 * Shown when a logged-in user's role does not permit access to a page or
 * action. Never shown for missing/invalid auth — that case redirects to
 * /login instead (see RequireAuth / RequireRole).
 */
export function AccessDenied({ message }: AccessDeniedProps) {
  const { currentUser } = useAuth();

  return (
    <Card>
      <div className="space-y-3 py-6 text-center">
        <h1 className="text-lg font-semibold text-slate-900">Zugriff verweigert</h1>
        <p className="mx-auto max-w-md text-sm text-slate-600">
          {message ??
            "Deine Rolle erlaubt keinen Zugriff auf diesen Bereich. Für manche Funktionen werden Admin-Rechte benötigt."}
        </p>
        {currentUser ? (
          <p className="text-sm text-slate-500">
            Aktuelle Rolle: <Badge tone="info">{currentUser.role}</Badge>
          </p>
        ) : null}
        <Link
          href="/"
          className="inline-block text-sm font-medium text-brand-600 hover:text-brand-700"
        >
          ← Zurück zum Dashboard
        </Link>
      </div>
    </Card>
  );
}
