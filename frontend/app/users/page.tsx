"use client";

import { useEffect, useState } from "react";

import { AccessDenied } from "@/components/auth/AccessDenied";
import { RequireRole } from "@/components/auth/RequireRole";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ComplianceNotice } from "@/components/ui/ComplianceNotice";
import { ApiError, getUsers } from "@/lib/api";
import type { User } from "@/lib/types";

type UsersState =
  | { status: "loading" }
  | { status: "loaded"; items: User[] }
  | { status: "forbidden" }
  | { status: "error"; message: string };

function formatDate(value: string): string {
  return new Date(value).toLocaleString("de-DE");
}

function UsersTable() {
  const [state, setState] = useState<UsersState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });

    getUsers()
      .then((response) => {
        if (!cancelled) {
          setState({ status: "loaded", items: response.items });
        }
      })
      .catch((err) => {
        if (cancelled) {
          return;
        }
        if (err instanceof ApiError && err.status === 403) {
          setState({ status: "forbidden" });
        } else {
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

  if (state.status === "loading") {
    return <p className="text-sm text-slate-500">Lade Benutzer…</p>;
  }

  if (state.status === "forbidden") {
    return (
      <AccessDenied message="Nur aktive Admin-Konten dürfen die Benutzerliste abrufen." />
    );
  }

  if (state.status === "error") {
    return <p className="text-sm text-rose-600">{state.message}</p>;
  }

  if (state.items.length === 0) {
    return <p className="text-sm text-slate-500">Noch keine Benutzer registriert.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs uppercase text-slate-400">
          <tr>
            <th className="pb-2 pr-4">E-Mail</th>
            <th className="pb-2 pr-4">Name</th>
            <th className="pb-2 pr-4">Rolle</th>
            <th className="pb-2 pr-4">Status</th>
            <th className="pb-2">Erstellt</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {state.items.map((user) => (
            <tr key={user.id}>
              <td className="py-2 pr-4 font-medium text-slate-900">{user.email}</td>
              <td className="py-2 pr-4 text-slate-600">{user.full_name ?? "—"}</td>
              <td className="py-2 pr-4">
                <Badge tone="info">{user.role}</Badge>
              </td>
              <td className="py-2 pr-4">
                <Badge tone={user.is_active ? "positive" : "negative"}>
                  {user.is_active ? "Aktiv" : "Deaktiviert"}
                </Badge>
              </td>
              <td className="py-2 text-slate-600">{formatDate(user.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function UsersPage() {
  return (
    <RequireRole
      allowedRoles={["admin"]}
      deniedMessage="Nur Admin-Konten dürfen die User-Verwaltung sehen."
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">User-Verwaltung</h1>
          <p className="mt-1 text-sm text-slate-600">
            Übersicht über alle registrierten Benutzerkonten und ihre Rollen.
          </p>
        </div>

        <ComplianceNotice />

        <Card title="Benutzer">
          <UsersTable />
        </Card>
      </div>
    </RequireRole>
  );
}
