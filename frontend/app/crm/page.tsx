"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { ComplianceNotice } from "@/components/ui/ComplianceNotice";
import {
  ApiError,
  listCrmCompanies,
  listCrmContacts,
  listCrmEmailDrafts,
  listCrmInteractions,
  listCrmLeads,
} from "@/lib/api";
import type { Company, Contact, EmailDraftRecord, Interaction, Lead } from "@/lib/types";

type ListState<T> =
  | { status: "loading" }
  | { status: "loaded"; items: T[] }
  | { status: "error"; message: string };

function useList<T>(fetcher: () => Promise<T[]>): ListState<T> {
  const [state, setState] = useState<ListState<T>>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });

    fetcher()
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return state;
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("de-DE");
}

function bodyPreview(body: string): string {
  const trimmed = body.trim();
  return trimmed.length > 140 ? `${trimmed.slice(0, 140)}…` : trimmed;
}

export default function CrmPage() {
  const companies = useList<Company>(listCrmCompanies);
  const leads = useList<Lead>(listCrmLeads);
  const contacts = useList<Contact>(listCrmContacts);
  const interactions = useList<Interaction>(listCrmInteractions);
  const emailDrafts = useList<EmailDraftRecord>(listCrmEmailDrafts);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">CRM</h1>
        <p className="mt-1 text-sm text-slate-600">
          Übersicht über die CRM-Daten, die der Sales Workflow automatisch
          anlegt oder aktualisiert.
        </p>
      </div>

      <ComplianceNotice />

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
                  <th className="pb-2 pr-4">Website/Domain</th>
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
                      {formatDate(company.created_at)}
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
                  <th className="pb-2 pr-4">Company ID</th>
                  <th className="pb-2 pr-4">Quelle</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Score</th>
                  <th className="pb-2">Erstellt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {leads.items.map((lead) => (
                  <tr key={lead.id}>
                    <td className="py-2 pr-4 font-mono text-xs text-slate-600">
                      {lead.company_id}
                    </td>
                    <td className="py-2 pr-4 text-slate-600">{lead.source}</td>
                    <td className="py-2 pr-4">
                      <Badge tone="info">{lead.status}</Badge>
                    </td>
                    <td className="py-2 pr-4 text-slate-600">{lead.score}</td>
                    <td className="py-2 text-slate-600">
                      {formatDate(lead.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card
        title="Email Drafts"
        description="Nur gespeicherte Entwürfe. Es wird keine E-Mail versendet."
      >
        {emailDrafts.status === "loading" ? (
          <p className="text-sm text-slate-500">Lade Email Drafts…</p>
        ) : emailDrafts.status === "error" ? (
          <p className="text-sm text-rose-600">{emailDrafts.message}</p>
        ) : emailDrafts.items.length === 0 ? (
          <p className="text-sm text-slate-500">Noch keine Email Drafts vorhanden.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-400">
                <tr>
                  <th className="pb-2 pr-4">Company ID</th>
                  <th className="pb-2 pr-4">Lead ID</th>
                  <th className="pb-2 pr-4">Workflow Run ID</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Betreff</th>
                  <th className="pb-2 pr-4">Vorschau</th>
                  <th className="pb-2">Erstellt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {emailDrafts.items.map((draft) => (
                  <tr key={draft.id}>
                    <td className="py-2 pr-4 font-mono text-xs text-slate-600">
                      {draft.company_id}
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-slate-600">
                      {draft.lead_id ?? "—"}
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs text-slate-600">
                      {draft.workflow_run_id ?? "—"}
                    </td>
                    <td className="py-2 pr-4">
                      <Badge tone="warning">{draft.status}</Badge>
                    </td>
                    <td className="py-2 pr-4 text-slate-600">
                      {draft.subject_lines[0] ?? "—"}
                    </td>
                    <td className="py-2 pr-4 max-w-xs text-slate-600">
                      {bodyPreview(draft.email_body)}
                    </td>
                    <td className="py-2 text-slate-600">
                      {formatDate(draft.created_at)}
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
          {contacts.status === "loading" ? (
            <p className="text-sm text-slate-500">Lade Contacts…</p>
          ) : contacts.status === "error" ? (
            <p className="text-sm text-rose-600">{contacts.message}</p>
          ) : contacts.items.length === 0 ? (
            <p className="text-sm text-slate-500">Noch keine Contacts vorhanden.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-400">
                  <tr>
                    <th className="pb-2 pr-4">Name</th>
                    <th className="pb-2 pr-4">Company ID</th>
                    <th className="pb-2">Erstellt</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {contacts.items.map((contact) => (
                    <tr key={contact.id}>
                      <td className="py-2 pr-4 font-medium text-slate-900">
                        {contact.first_name} {contact.last_name}
                      </td>
                      <td className="py-2 pr-4 font-mono text-xs text-slate-600">
                        {contact.company_id}
                      </td>
                      <td className="py-2 text-slate-600">
                        {formatDate(contact.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
        <Card title="Interactions">
          {interactions.status === "loading" ? (
            <p className="text-sm text-slate-500">Lade Interactions…</p>
          ) : interactions.status === "error" ? (
            <p className="text-sm text-rose-600">{interactions.message}</p>
          ) : interactions.items.length === 0 ? (
            <p className="text-sm text-slate-500">Noch keine Interactions vorhanden.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-400">
                  <tr>
                    <th className="pb-2 pr-4">Typ</th>
                    <th className="pb-2 pr-4">Status</th>
                    <th className="pb-2">Erstellt</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {interactions.items.map((interaction) => (
                    <tr key={interaction.id}>
                      <td className="py-2 pr-4 text-slate-600">{interaction.type}</td>
                      <td className="py-2 pr-4">
                        <Badge tone="neutral">{interaction.status ?? "—"}</Badge>
                      </td>
                      <td className="py-2 text-slate-600">
                        {formatDate(interaction.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
