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
  createOfferProfile,
  deactivateOfferProfile,
  getOfferProfiles,
  previewOffer,
  updateOfferProfile,
} from "@/lib/api";
import { canDeactivateSalesStrategyProfile, canManageSalesStrategy } from "@/lib/roles";
import type { OfferPreviewResponse, OfferProfile } from "@/lib/types";

function linesToList(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function listToLines(value: string[]): string {
  return value.join("\n");
}

const EMPTY_FORM = {
  name: "",
  main_value_proposition: "",
  description: "",
  target_outcome: "",
  pain_points_solved: "",
  key_benefits: "",
  differentiators: "",
  proof_points: "",
  call_to_action: "",
  tone: "professional",
  language: "de",
  forbidden_claims: "",
  required_disclaimers: "",
  is_active: true,
};

export default function OfferProfilesPage() {
  const { currentUser } = useAuth();
  const canManage = canManageSalesStrategy(currentUser);
  const canDeactivate = canDeactivateSalesStrategyProfile(currentUser);

  const [profiles, setProfiles] = useState<OfferProfile[] | null>(null);
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
      const response = await getOfferProfiles();
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

  function startEdit(profile: OfferProfile) {
    setEditingId(profile.id);
    setForm({
      name: profile.name,
      main_value_proposition: profile.main_value_proposition,
      description: profile.description ?? "",
      target_outcome: profile.target_outcome ?? "",
      pain_points_solved: listToLines(profile.pain_points_solved),
      key_benefits: listToLines(profile.key_benefits),
      differentiators: listToLines(profile.differentiators),
      proof_points: listToLines(profile.proof_points),
      call_to_action: profile.call_to_action ?? "",
      tone: profile.tone,
      language: profile.language,
      forbidden_claims: listToLines(profile.forbidden_claims),
      required_disclaimers: listToLines(profile.required_disclaimers),
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
      main_value_proposition: form.main_value_proposition.trim(),
      description: form.description.trim() || null,
      target_outcome: form.target_outcome.trim() || null,
      pain_points_solved: linesToList(form.pain_points_solved),
      key_benefits: linesToList(form.key_benefits),
      differentiators: linesToList(form.differentiators),
      proof_points: linesToList(form.proof_points),
      call_to_action: form.call_to_action.trim() || null,
      tone: form.tone.trim() || "professional",
      language: form.language.trim() || "de",
      forbidden_claims: linesToList(form.forbidden_claims),
      required_disclaimers: linesToList(form.required_disclaimers),
      is_active: form.is_active,
    };
    try {
      if (editingId) {
        await updateOfferProfile(editingId, payload);
      } else {
        await createOfferProfile(payload);
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
      await deactivateOfferProfile(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    }
  }

  // -- preview ----------------------------------------------------------------

  const [previewId, setPreviewId] = useState("");
  const [previewing, setPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [previewResult, setPreviewResult] = useState<OfferPreviewResponse | null>(null);

  async function handlePreview(event: React.FormEvent) {
    event.preventDefault();
    if (!previewId) {
      setPreviewError("Bitte ein Offer Profil auswählen.");
      return;
    }
    setPreviewing(true);
    setPreviewError(null);
    setPreviewResult(null);
    try {
      const result = await previewOffer({ offer_profile_id: previewId });
      setPreviewResult(result);
    } catch (err) {
      setPreviewError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setPreviewing(false);
    }
  }

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Offer Profile</h1>
          <p className="mt-1 text-sm text-slate-600">
            Offer Profile beschreiben, was verkauft wird, und steuern die
            Positionierung der Email Drafts.
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Grundlage für alles Weitere: Offer und{" "}
            <a href="/sales-strategy/icp" className="underline hover:no-underline">
              ICP
            </a>{" "}
            zuerst definieren, danach Leads sourcen und qualifizieren.
          </p>
        </div>

        <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
          <ul className="list-inside list-disc space-y-1">
            <li>Offer Profile steuert die Positionierung der Email Drafts.</li>
            <li>Keine falschen Versprechen eintragen.</li>
            <li>Proof Points nur verwenden, wenn sie stimmen.</li>
            <li>Es werden keine E-Mails automatisch gesendet.</li>
          </ul>
        </div>

        {canManage ? (
          <Card title={editingId ? "Offer bearbeiten" : "Neues Offer erstellen"}>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <Input
                label="Name *"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
              <Textarea
                label="Value Proposition *"
                required
                value={form.main_value_proposition}
                onChange={(e) =>
                  setForm({ ...form, main_value_proposition: e.target.value })
                }
              />
              <Textarea
                label="Beschreibung"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
              <Input
                label="Target Outcome"
                value={form.target_outcome}
                onChange={(e) => setForm({ ...form, target_outcome: e.target.value })}
              />
              <div className="grid gap-4 sm:grid-cols-2">
                <Textarea
                  label="Gelöste Pain Points (einer pro Zeile)"
                  value={form.pain_points_solved}
                  onChange={(e) =>
                    setForm({ ...form, pain_points_solved: e.target.value })
                  }
                />
                <Textarea
                  label="Key Benefits (einer pro Zeile)"
                  value={form.key_benefits}
                  onChange={(e) => setForm({ ...form, key_benefits: e.target.value })}
                />
                <Textarea
                  label="Differenzierungsmerkmale (einer pro Zeile)"
                  value={form.differentiators}
                  onChange={(e) =>
                    setForm({ ...form, differentiators: e.target.value })
                  }
                />
                <Textarea
                  label="Proof Points (einer pro Zeile — nur wenn sie stimmen)"
                  value={form.proof_points}
                  onChange={(e) => setForm({ ...form, proof_points: e.target.value })}
                />
                <Textarea
                  label="Verbotene Aussagen / forbidden_claims (eine pro Zeile)"
                  value={form.forbidden_claims}
                  onChange={(e) =>
                    setForm({ ...form, forbidden_claims: e.target.value })
                  }
                  hint="Diese Aussagen werden im Sales Workflow aktiv vermieden."
                />
                <Textarea
                  label="Pflicht-Disclaimer (einer pro Zeile)"
                  value={form.required_disclaimers}
                  onChange={(e) =>
                    setForm({ ...form, required_disclaimers: e.target.value })
                  }
                />
              </div>
              <Input
                label="Call to Action"
                value={form.call_to_action}
                onChange={(e) => setForm({ ...form, call_to_action: e.target.value })}
              />
              <div className="grid gap-4 sm:grid-cols-3">
                <Input
                  label="Tone"
                  value={form.tone}
                  onChange={(e) => setForm({ ...form, tone: e.target.value })}
                />
                <Input
                  label="Language"
                  value={form.language}
                  onChange={(e) => setForm({ ...form, language: e.target.value })}
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
                  {editingId ? "Speichern" : "Offer erstellen"}
                </Button>
                {editingId ? (
                  <Button type="button" variant="ghost" onClick={resetForm}>
                    Abbrechen
                  </Button>
                ) : null}
              </div>
              {formError ? <p className="text-sm text-rose-400">{formError}</p> : null}
            </form>
          </Card>
        ) : null}

        <Card title="Offer Preview">
          <form className="space-y-4" onSubmit={handlePreview}>
            <div>
              <label className="field-label" htmlFor="offer-select">
                Offer Profil *
              </label>
              <select
                id="offer-select"
                className="w-full rounded-lg border border-slate-300 bg-canvas px-3 py-2 text-sm text-slate-900 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                value={previewId}
                onChange={(e) => setPreviewId(e.target.value)}
              >
                <option value="">Bitte wählen…</option>
                {(profiles ?? []).map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.name}
                  </option>
                ))}
              </select>
            </div>
            <Button type="submit" loading={previewing}>
              Preview generieren
            </Button>
            {previewError ? (
              <p className="text-sm text-rose-400">{previewError}</p>
            ) : null}
          </form>

          {previewResult ? (
            <div className="mt-4 space-y-3 border-t border-slate-100 pt-4">
              <div>
                <p className="text-xs font-semibold uppercase text-slate-500">
                  Summary
                </p>
                <p className="text-sm text-slate-700">{previewResult.summary}</p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase text-slate-500">
                  Positioning
                </p>
                <p className="text-sm text-slate-700">{previewResult.positioning}</p>
              </div>
              {previewResult.suggested_cta ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-slate-500">
                    Suggested CTA
                  </p>
                  <p className="text-sm text-slate-700">
                    {previewResult.suggested_cta}
                  </p>
                </div>
              ) : null}
              {previewResult.warnings.length > 0 ? (
                <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
                  {previewResult.warnings.map((w) => (
                    <p key={w}>{w}</p>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </Card>

        <Card title="Alle Offer Profile">
          {loading ? (
            <p className="text-sm text-slate-500">Offer Profile werden geladen…</p>
          ) : error ? (
            <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </div>
          ) : profiles && profiles.length > 0 ? (
            <div className="space-y-3">
              {profiles.map((profile) => (
                <div
                  key={profile.id}
                  className="rounded-lg border border-slate-200 bg-surface px-4 py-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {profile.name}
                      </p>
                      <p className="text-sm text-slate-600">
                        {profile.main_value_proposition}
                      </p>
                    </div>
                    <Badge tone={profile.is_active ? "positive" : "neutral"}>
                      {profile.is_active ? "aktiv" : "inaktiv"}
                    </Badge>
                  </div>
                  <dl className="mt-2 space-y-1 text-xs text-slate-600">
                    {profile.target_outcome ? (
                      <p>Target Outcome: {profile.target_outcome}</p>
                    ) : null}
                    {profile.pain_points_solved.length > 0 ? (
                      <p>Gelöste Pain Points: {profile.pain_points_solved.join(", ")}</p>
                    ) : null}
                    {profile.key_benefits.length > 0 ? (
                      <p>Key Benefits: {profile.key_benefits.join(", ")}</p>
                    ) : null}
                    {profile.differentiators.length > 0 ? (
                      <p>Differenzierung: {profile.differentiators.join(", ")}</p>
                    ) : null}
                    {profile.proof_points.length > 0 ? (
                      <p>Proof Points: {profile.proof_points.join(", ")}</p>
                    ) : null}
                    {profile.call_to_action ? (
                      <p>CTA: {profile.call_to_action}</p>
                    ) : null}
                    <p>
                      Tone: {profile.tone} · Language: {profile.language}
                    </p>
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
            <p className="text-sm text-slate-500">Noch keine Offer Profile vorhanden.</p>
          )}
        </Card>
      </div>
    </RequireAuth>
  );
}
