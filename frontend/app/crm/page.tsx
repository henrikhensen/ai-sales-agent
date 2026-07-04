"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ApiError, getJson } from "@/lib/api";
import type { Company, Lead } from "@/lib/types";

type ListState<T> =
  | { status: "loading" }
  | { status: "loaded"; items: T[] }
  | { status: "error"; message: string };

function useList<T>(path: string): ListState<T> {
  const [state, setState] = useState<ListState<T>>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });

    getJson<T[]>(path)
      .then((items) => {
        if (!cancelled) {
          setState({ status: "loaded", items });
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            status: "error",
            message: err instanceof ApiError ? err.message : "Unbekannter Fehler.",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [path]);

  return state;
}

export default function CrmPage() {
  const companies = useList<Company>("/api/v1/companies");
  const leads = useList<Lead>("/api/v1/leads");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">CRM</h1>
        <p className="mt-1 text-sm text-slate-600">
          Einfache Übersicht über die vorhandenen CRM-Daten aus dem Backend.
        </p>
      </div>

      <Card title="Companies">
        {companies.status === "loading" ? (
          <p className="text-sm text-slate-500">Lade Companies…</p>
        ) : companies.status === "error" ? (
          <p className="text-sm text-rose-600">{companies.message}</p>
        ) : companies.items.length === 0 ? (
          <p className="text-sm text-slate-500">Noch keine Companies vorhanden.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-400">
                <tr>
                  <th className="pb-2 pr-4">Name</th>
                  <th className="pb-2 pr-4">Domain</th>
                  <th className="pb-2 pr-4">Branche</th>
                  <th className="pb-2">Erstellt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {companies.items.map((company) => (
                  <tr key={company.id}>
                    <td className="py-2 pr-4 font-medium text-slate-900">
                      {company.name}
                    </td>
                    <td className="py-2 pr-4 text-slate-600">
                      {company.domain ?? "—"}
                    </td>
                    <td className="py-2 pr-4 text-slate-600">
                      {company.industry ?? "—"}
                    </td>
                    <td className="py-2 text-slate-600">
                      {new Date(company.created_at).toLocaleDateString("de-DE")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Leads">
        {leads.status === "loading" ? (
          <p className="text-sm text-slate-500">Lade Leads…</p>
        ) : leads.status === "error" ? (
          <p className="text-sm text-rose-600">{leads.message}</p>
        ) : leads.items.length === 0 ? (
          <p className="text-sm text-slate-500">Noch keine Leads vorhanden.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-400">
                <tr>
                  <th className="pb-2 pr-4">Quelle</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Score</th>
                  <th className="pb-2">Erstellt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {leads.items.map((lead) => (
                  <tr key={lead.id}>
                    <td className="py-2 pr-4 text-slate-600">{lead.source}</td>
                    <td className="py-2 pr-4">
                      <Badge tone="info">{lead.status}</Badge>
                    </td>
                    <td className="py-2 pr-4 text-slate-600">{lead.score}</td>
                    <td className="py-2 text-slate-600">
                      {new Date(lead.created_at).toLocaleDateString("de-DE")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card title="Contacts">
          <p className="text-sm text-slate-500">
            Für Contacts steht aktuell noch kein Backend-Endpoint zur Verfügung.
            Diese Ansicht wird angebunden, sobald die entsprechende API
            existiert.
          </p>
        </Card>
        <Card title="Interactions">
          <p className="text-sm text-slate-500">
            Für Interactions steht aktuell noch kein Backend-Endpoint zur
            Verfügung. Diese Ansicht wird angebunden, sobald die entsprechende
            API existiert.
          </p>
        </Card>
      </div>
    </div>
  );
}
