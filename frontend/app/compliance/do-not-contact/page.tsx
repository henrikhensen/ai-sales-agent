"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import {
  ApiError,
  checkDoNotContact,
  createDoNotContactEntry,
  deactivateDoNotContactEntry,
  getDoNotContactEntries,
  updateDoNotContactEntry,
} from "@/lib/api";
import { canCreateDoNotContactEntry, canManageDoNotContactEntry } from "@/lib/roles";
import type { DoNotContactCheckResponse, DoNotContactEntry } from "@/lib/types";

function formatDate(value: string): string {
  return new Date(value).toLocaleString("de-DE");
}

interface EntryRowProps {
  entry: DoNotContactEntry;
  canManage: boolean;
  onChanged: () => void;
}

function EntryRow({ entry, canManage, onChanged }: EntryRowProps) {
  const [editing, setEditing] = useState(false);
  const [reason, setReason] = useState(entry.reason);
  const [saving, setSaving] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSaveReason() {
    setSaving(true);
    setError(null);
    try {
      await updateDoNotContactEntry(entry.id, { reason });
      setEditing(false);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate() {
    setDeactivating(true);
    setError(null);
    try {
      await deactivateDoNotContactEntry(entry.id);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setDeactivating(false);
    }
  }

  return (
    <tr className="border-b border-slate-100 align-top">
      <td className="py-2 pr-4 text-sm text-slate-900">{entry.email ?? "—"}</td>
      <td className="py-2 pr-4 text-sm text-slate-900">{entry.domain ?? "—"}</td>
      <td className="py-2 pr-4 text-sm text-slate-900">{entry.company_name ?? "—"}</td>
      <td className="py-2 pr-4 text-sm text-slate-700">
        {editing ? (
          <div className="space-y-2">
            <Input
              label="Reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
            <div className="flex gap-2">
              <Button variant="secondary" onClick={handleSaveReason} loading={saving}>
                Speichern
              </Button>
              <Button variant="ghost" onClick={() => setEditing(false)}>
                Abbrechen
              </Button>
            </div>
          </div>
        ) : (
          entry.reason
        )}
      </td>
      <td className="py-2 pr-4 text-sm text-slate-700">{entry.source}</td>
      <td className="py-2 pr-4">
        <Badge tone={entry.is_active ? "positive" : "neutral"}>
          {entry.is_active ? "Active" : "Inactive"}
        </Badge>
      </td>
      <td className="py-2 pr-4 text-xs text-slate-500">{formatDate(entry.created_at)}</td>
      <td className="py-2 pr-4">
        {canManage ? (
          <div className="space-y-1">
            {!editing ? (
              <Button variant="ghost" onClick={() => setEditing(true)}>
                Bearbeiten
              </Button>
            ) : null}
            {entry.is_active ? (
              <Button
                variant="secondary"
                onClick={handleDeactivate}
                loading={deactivating}
              >
                Deaktivieren
              </Button>
            ) : null}
            {error ? <p className="text-xs text-rose-600">{error}</p> : null}
          </div>
        ) : null}
      </td>
    </tr>
  );
}

export default function DoNotContactPage() {
  const { currentUser } = useAuth();
  const canCreate = canCreateDoNotContactEntry(currentUser);
  const canManage = canManageDoNotContactEntry(currentUser);

  const [entries, setEntries] = useState<DoNotContactEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadEntries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getDoNotContactEntries();
      setEntries(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  // -- create form ------------------------------------------------------------
  const [email, setEmail] = useState("");
  const [domain, setDomain] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [reason, setReason] = useState("");
  const [source, setSource] = useState("manual");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSuccess, setCreateSuccess] = useState(false);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setCreating(true);
    setCreateError(null);
    setCreateSuccess(false);
    try {
      await createDoNotContactEntry({
        email: email.trim() || null,
        domain: domain.trim() || null,
        company_name: companyName.trim() || null,
        reason: reason.trim(),
        source: source.trim() || "manual",
      });
      setEmail("");
      setDomain("");
      setCompanyName("");
      setReason("");
      setSource("manual");
      setCreateSuccess(true);
      await loadEntries();
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setCreating(false);
    }
  }

  // -- check form ---------------------------------------------------------------
  const [checkEmail, setCheckEmail] = useState("");
  const [checkDomain, setCheckDomain] = useState("");
  const [checkCompanyName, setCheckCompanyName] = useState("");
  const [checking, setChecking] = useState(false);
  const [checkError, setCheckError] = useState<string | null>(null);
  const [checkResult, setCheckResult] = useState<DoNotContactCheckResponse | null>(null);

  async function handleCheck(event: React.FormEvent) {
    event.preventDefault();
    setChecking(true);
    setCheckError(null);
    setCheckResult(null);
    try {
      const result = await checkDoNotContact({
        email: checkEmail.trim() || null,
        domain: checkDomain.trim() || null,
        company_name: checkCompanyName.trim() || null,
      });
      setCheckResult(result);
    } catch (err) {
      setCheckError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Do-not-contact</h1>
          <p className="mt-1 text-sm text-slate-600">
            Opt-out-Liste für E-Mails, Domains und Firmen — hat Vorrang vor
            Sales Workflow und Human Review.
          </p>
        </div>

        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          <ul className="list-inside list-disc space-y-1">
            <li>Do-not-contact blockiert Email Draft Erstellung.</li>
            <li>Do-not-contact blockiert Review Approval.</li>
            <li>Es werden keine E-Mails automatisch versendet.</li>
            <li>Approved bedeutet nicht Versand.</li>
            <li>Inaktive Einträge blockieren nicht.</li>
          </ul>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {canCreate ? (
            <Card title="Neuer Eintrag">
              <form className="space-y-4" onSubmit={handleCreate}>
                <Input
                  label="Email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  hint="Optional — mindestens eines von Email, Domain, Company muss gesetzt sein."
                />
                <Input
                  label="Domain"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                />
                <Input
                  label="Company Name"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
                <Input
                  label="Reason *"
                  required
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
                <Input
                  label="Source"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  hint="Standard: manual"
                />
                <Button type="submit" loading={creating}>
                  Eintrag erstellen
                </Button>
                {createSuccess ? (
                  <p className="text-xs text-emerald-700">Eintrag wurde erstellt.</p>
                ) : null}
                {createError ? (
                  <p className="text-xs text-rose-600">{createError}</p>
                ) : null}
              </form>
            </Card>
          ) : null}

          <Card title="Check">
            <form className="space-y-4" onSubmit={handleCheck}>
              <Input
                label="Email"
                type="email"
                value={checkEmail}
                onChange={(e) => setCheckEmail(e.target.value)}
              />
              <Input
                label="Domain"
                value={checkDomain}
                onChange={(e) => setCheckDomain(e.target.value)}
              />
              <Input
                label="Company Name"
                value={checkCompanyName}
                onChange={(e) => setCheckCompanyName(e.target.value)}
              />
              <Button type="submit" loading={checking}>
                Prüfen
              </Button>
              {checkError ? <p className="text-xs text-rose-600">{checkError}</p> : null}
              {checkResult ? (
                <div
                  className={`rounded-lg border px-3 py-2 text-sm ${
                    checkResult.is_blocked
                      ? "border-rose-200 bg-rose-50 text-rose-800"
                      : "border-emerald-200 bg-emerald-50 text-emerald-800"
                  }`}
                >
                  <p className="font-medium">
                    {checkResult.is_blocked ? "Blockiert" : "Nicht blockiert"}
                  </p>
                  {checkResult.is_blocked ? (
                    <>
                      <p className="mt-1">Matched by: {checkResult.matched_by}</p>
                      <p>Reason: {checkResult.reason}</p>
                    </>
                  ) : null}
                </div>
              ) : null}
            </form>
          </Card>
        </div>

        <Card title="Alle Einträge">
          {loading ? (
            <p className="text-sm text-slate-500">Einträge werden geladen…</p>
          ) : error ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </div>
          ) : entries && entries.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 text-left text-xs font-semibold uppercase tracking-wide text-slate-400">
                    <th className="py-2 pr-4">Email</th>
                    <th className="py-2 pr-4">Domain</th>
                    <th className="py-2 pr-4">Company</th>
                    <th className="py-2 pr-4">Reason</th>
                    <th className="py-2 pr-4">Source</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2 pr-4">Created At</th>
                    <th className="py-2 pr-4">Aktionen</th>
                  </tr>
                </thead>
                <tbody>
                  {entries.map((entry) => (
                    <EntryRow
                      key={entry.id}
                      entry={entry}
                      canManage={canManage}
                      onChanged={loadEntries}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Keine Einträge vorhanden.</p>
          )}
        </Card>
      </div>
    </RequireAuth>
  );
}
