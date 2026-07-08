"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import {
  ApiError,
  checkICPFit,
  createICPProfile,
  deactivateICPProfile,
  getICPProfiles,
  updateICPProfile,
} from "@/lib/api";
import { canDeactivateSalesStrategyProfile, canManageSalesStrategy } from "@/lib/roles";
import type { ICPFitCheckResponse, ICPProfile } from "@/lib/types";

function linesToList(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function listToLines(value: string[]): string {
  return value.join("\n");
}

const FIT_LEVEL_TONE: Record<string, "positive" | "info" | "warning" | "negative" | "neutral"> = {
  excellent: "positive",
  good: "positive",
  medium: "info",
  weak: "warning",
  not_fit: "negative",
};

const EMPTY_FORM = {
  name: "",
  description: "",
  target_industries: "",
  excluded_industries: "",
  target_keywords: "",
  negative_keywords: "",
  target_pain_points: "",
  buying_triggers: "",
  minimum_fit_score: "70",
  is_active: true,
};

export default function ICPProfilesPage() {
  const { currentUser } = useAuth();
  const canManage = canManageSalesStrategy(currentUser);
  const canDeactivate = canDeactivateSalesStrategyProfile(currentUser);

  const [profiles, setProfiles] = useState<ICPProfile[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getICPProfiles();
      setProfiles(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function startEdit(profile: ICPProfile) {
    setEditingId(profile.id);
    setForm({
      name: profile.name,
      description: profile.description ?? "",
      target_industries: listToLines(profile.target_industries),
      excluded_industries: listToLines(profile.excluded_industries),
      target_keywords: listToLines(profile.target_keywords),
      negative_keywords: listToLines(profile.negative_keywords),
      target_pain_points: listToLines(profile.target_pain_points),
      buying_triggers: listToLines(profile.buying_triggers),
      minimum_fit_score: String(profile.minimum_fit_score),
      is_active: profile.is_active,
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setFormError(null);
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setFormError(null);
    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      target_industries: linesToList(form.target_industries),
      excluded_industries: linesToList(form.excluded_industries),
      target_keywords: linesToList(form.target_keywords),
      negative_keywords: linesToList(form.negative_keywords),
      target_pain_points: linesToList(form.target_pain_points),
      buying_triggers: linesToList(form.buying_triggers),
      minimum_fit_score: Number(form.minimum_fit_score) || 70,
      is_active: form.is_active,
    };
    try {
      if (editingId) {
        await updateICPProfile(editingId, payload);
      } else {
        await createICPProfile(payload);
      }
      resetForm();
      await load();
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeactivate(id: string) {
    try {
      await deactivateICPProfile(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  // -- fit check ------------------------------------------------------------

  const [fitForm, setFitForm] = useState({
    icp_profile_id: "",
    company_name: "",
    industry: "",
    location: "",
    company_size: "",
    website_text: "",
    keywords: "",
  });
  const [fitChecking, setFitChecking] = useState(false);
  const [fitError, setFitError] = useState<string | null>(null);
  const [fitResult, setFitResult] = useState<ICPFitCheckResponse | null>(null);

  async function handleFitCheck(event: React.FormEvent) {
    event.preventDefault();
    if (!fitForm.icp_profile_id) {
      setFitError("Bitte ein ICP Profil auswählen.");
      return;
    }
    setFitChecking(true);
    setFitError(null);
    setFitResult(null);
    try {
      const result = await checkICPFit({
        icp_profile_id: fitForm.icp_profile_id,
        company_name: fitForm.company_name || undefined,
        industry: fitForm.industry || undefined,
        location: fitForm.location || undefined,
        company_size: fitForm.company_size || undefined,
        website_text: fitForm.website_text || undefined,
        keywords: linesToList(fitForm.keywords),
      });
      setFitResult(result);
    } catch (err) {
      setFitError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setFitChecking(false);
    }
  }

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">ICP Profile</h1>
          <p className="mt-1 text-sm text-slate-600">
            Ideal Customer Profiles beschreiben, welche Firmen/Leads gut zum
            Angebot passen — nur zur Bewertung vorhandener Daten.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Empfohlener Ablauf: Offer &amp; ICP definieren → Leads sourcen →
            qualifizieren → Outreach Queue bauen → Drafts vorbereiten und
            reviewen. Nächster Schritt nach dem ICP:{" "}
            <a href="/lead-sourcing" className="underline hover:no-underline">
              Lead Sourcing
            </a>
            .
          </p>
        </div>

        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <ul className="list-inside list-disc space-y-1">
            <li>ICP hilft dem Agenten, passende Kunden zu bewerten.</li>
            <li>ICP ist keine automatische Kontaktaufnahme.</li>
            <li>Schlechter Fit sollte nicht kontaktiert werden.</li>
          </ul>
        </div>

        {canManage ? (
          <Card title={editingId ? "ICP bearbeiten" : "Neues ICP erstellen"}>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <Input
                label="Name *"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
              <Textarea
                label="Beschreibung"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Textarea
                  label="Zielbranchen (eine pro Zeile)"
                  value={form.target_industries}
                  onChange={(e) =>
                    setForm({ ...form, target_industries: e.target.value })
                  }
                />
                <Textarea
                  label="Ausgeschlossene Branchen (eine pro Zeile)"
                  value={form.excluded_industries}
                  onChange={(e) =>
                    setForm({ ...form, excluded_industries: e.target.value })
                  }
                />
                <Textarea
                  label="Zielkeywords (eines pro Zeile)"
                  value={form.target_keywords}
                  onChange={(e) =>
                    setForm({ ...form, target_keywords: e.target.value })
                  }
                />
                <Textarea
                  label="Negative Keywords (eines pro Zeile)"
                  value={form.negative_keywords}
                  onChange={(e) =>
                    setForm({ ...form, negative_keywords: e.target.value })
                  }
                />
                <Textarea
                  label="Pain Points (einer pro Zeile)"
                  value={form.target_pain_points}
                  onChange={(e) =>
                    setForm({ ...form, target_pain_points: e.target.value })
                  }
                />
                <Textarea
                  label="Buying Triggers (einer pro Zeile)"
                  value={form.buying_triggers}
                  onChange={(e) =>
                    setForm({ ...form, buying_triggers: e.target.value })
                  }
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Minimum Fit Score"
                  type="number"
                  min={0}
                  max={100}
                  value={form.minimum_fit_score}
                  onChange={(e) =>
                    setForm({ ...form, minimum_fit_score: e.target.value })
                  }
                />
                <label className="flex items-center gap-2 pt-6 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                    checked={form.is_active}
                    onChange={(e) =>
                      setForm({ ...form, is_active: e.target.checked })
                    }
                  />
                  Aktiv
                </label>
              </div>
              <div className="flex gap-2">
                <Button type="submit" loading={saving}>
                  {editingId ? "Speichern" : "ICP erstellen"}
                </Button>
                {editingId ? (
                  <Button type="button" variant="ghost" onClick={resetForm}>
                    Abbrechen
                  </Button>
                ) : null}
              </div>
              {formError ? <p className="text-sm text-rose-600">{formError}</p> : null}
            </form>
          </Card>
        ) : null}

        <Card title="ICP Fit Check">
          <form className="space-y-4" onSubmit={handleFitCheck}>
            <div>
              <label className="field-label" htmlFor="icp-select">
                ICP Profil *
              </label>
              <select
                id="icp-select"
                className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                value={fitForm.icp_profile_id}
                onChange={(e) =>
                  setFitForm({ ...fitForm, icp_profile_id: e.target.value })
                }
              >
                <option value="">Bitte wählen…</option>
                {(profiles ?? []).map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Company Name"
                value={fitForm.company_name}
                onChange={(e) =>
                  setFitForm({ ...fitForm, company_name: e.target.value })
                }
              />
              <Input
                label="Industry"
                value={fitForm.industry}
                onChange={(e) => setFitForm({ ...fitForm, industry: e.target.value })}
              />
              <Input
                label="Location"
                value={fitForm.location}
                onChange={(e) => setFitForm({ ...fitForm, location: e.target.value })}
              />
              <Input
                label="Company Size"
                value={fitForm.company_size}
                onChange={(e) =>
                  setFitForm({ ...fitForm, company_size: e.target.value })
                }
              />
            </div>
            <Textarea
              label="Website Text / Notizen"
              value={fitForm.website_text}
              onChange={(e) =>
                setFitForm({ ...fitForm, website_text: e.target.value })
              }
              hint="Bereits vorhandener Text — es wird nichts neu abgerufen."
            />
            <Textarea
              label="Keywords (eines pro Zeile)"
              value={fitForm.keywords}
              onChange={(e) => setFitForm({ ...fitForm, keywords: e.target.value })}
            />
            <Button type="submit" loading={fitChecking}>
              Fit Check ausführen
            </Button>
            {fitError ? <p className="text-sm text-rose-600">{fitError}</p> : null}
          </form>

          {fitResult ? (
            <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
              <div className="flex items-center gap-3">
                <Badge tone={FIT_LEVEL_TONE[fitResult.fit_level] ?? "neutral"}>
                  {fitResult.fit_level}
                </Badge>
                <span className="text-sm font-medium text-slate-900">
                  Fit Score: {fitResult.fit_score} / 100
                </span>
              </div>
              <p className="text-sm text-slate-700">{fitResult.recommendation}</p>
              {fitResult.matched_signals.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-slate-500">
                    Matched Signals
                  </p>
                  <ul className="list-inside list-disc text-sm text-slate-700">
                    {fitResult.matched_signals.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {fitResult.missing_signals.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-slate-500">
                    Missing Signals
                  </p>
                  <ul className="list-inside list-disc text-sm text-slate-700">
                    {fitResult.missing_signals.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {fitResult.negative_signals.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-rose-500">
                    Negative Signals
                  </p>
                  <ul className="list-inside list-disc text-sm text-rose-700">
                    {fitResult.negative_signals.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {fitResult.warnings.length > 0 ? (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  {fitResult.warnings.map((w) => (
                    <p key={w}>{w}</p>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </Card>

        <Card title="Alle ICP Profile">
          {loading ? (
            <p className="text-sm text-slate-500">ICP Profile werden geladen…</p>
          ) : error ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
              {error}
            </div>
          ) : profiles && profiles.length > 0 ? (
            <div className="space-y-3">
              {profiles.map((profile) => (
                <div
                  key={profile.id}
                  className="rounded-lg border border-slate-200 bg-white px-4 py-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {profile.name}
                      </p>
                      {profile.description ? (
                        <p className="text-sm text-slate-600">{profile.description}</p>
                      ) : null}
                    </div>
                    <Badge tone={profile.is_active ? "positive" : "neutral"}>
                      {profile.is_active ? "aktiv" : "inaktiv"}
                    </Badge>
                  </div>
                  <dl className="mt-2 space-y-1 text-xs text-slate-600">
                    {profile.target_industries.length > 0 ? (
                      <p>Zielbranchen: {profile.target_industries.join(", ")}</p>
                    ) : null}
                    {profile.excluded_industries.length > 0 ? (
                      <p>
                        Ausgeschlossene Branchen:{" "}
                        {profile.excluded_industries.join(", ")}
                      </p>
                    ) : null}
                    {profile.target_keywords.length > 0 ? (
                      <p>Zielkeywords: {profile.target_keywords.join(", ")}</p>
                    ) : null}
                    {profile.negative_keywords.length > 0 ? (
                      <p>Negative Keywords: {profile.negative_keywords.join(", ")}</p>
                    ) : null}
                    {profile.target_pain_points.length > 0 ? (
                      <p>Pain Points: {profile.target_pain_points.join(", ")}</p>
                    ) : null}
                    {profile.buying_triggers.length > 0 ? (
                      <p>Buying Triggers: {profile.buying_triggers.join(", ")}</p>
                    ) : null}
                    <p>Minimum Fit Score: {profile.minimum_fit_score}</p>
                  </dl>
                  {canManage ? (
                    <div className="mt-3 flex gap-2">
                      <Button variant="ghost" onClick={() => startEdit(profile)}>
                        Bearbeiten
                      </Button>
                      {canDeactivate && profile.is_active ? (
                        <Button
                          variant="ghost"
                          onClick={() => handleDeactivate(profile.id)}
                        >
                          Deaktivieren
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Noch keine ICP Profile vorhanden.</p>
          )}
        </Card>
      </div>
    </RequireAuth>
  );
}
