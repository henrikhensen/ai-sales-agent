"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireAuth } from "@/components/auth/RequireAuth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  ApiError,
  getAdminControls,
  getAdminSetupChecklist,
  getICPProfiles,
  getOfferProfiles,
  getWorkspaceSettings,
  updateAdminControls,
  updateWorkspaceSettings,
} from "@/lib/api";
import type {
  AdminControlsStatus,
  ChecklistItemStatus,
  CustomerSetupChecklistResponse,
  ICPProfile,
  OfferProfile,
  WorkspaceSettings,
} from "@/lib/types";

const CHECKLIST_TONE: Record<ChecklistItemStatus, "positive" | "warning" | "negative" | "neutral"> = {
  passed: "positive",
  warning: "warning",
  blocker: "negative",
  not_checked: "neutral",
};

export default function AdminControlsPage() {
  const [workspace, setWorkspace] = useState<WorkspaceSettings | null>(null);
  const [controls, setControls] = useState<AdminControlsStatus | null>(null);
  const [checklist, setChecklist] = useState<CustomerSetupChecklistResponse | null>(null);
  const [icpProfiles, setIcpProfiles] = useState<ICPProfile[]>([]);
  const [offerProfiles, setOfferProfiles] = useState<OfferProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [workspaceForm, setWorkspaceForm] = useState({
    workspace_name: "",
    company_name: "",
    company_website: "",
    default_language: "",
    default_tone: "",
    default_icp_profile_id: "",
    default_offer_profile_id: "",
  });
  const [workspaceSaving, setWorkspaceSaving] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [workspaceNote, setWorkspaceNote] = useState<string | null>(null);

  const [controlsForm, setControlsForm] = useState({
    allow_real_llm_calls: false,
    allow_real_email_drafts: false,
    allow_real_reply_reads: false,
    allow_real_dispatch: false,
    dispatch_mode: "draft_only" as "draft_only" | "manual_send",
  });
  const [controlsSaving, setControlsSaving] = useState(false);
  const [controlsError, setControlsError] = useState<string | null>(null);
  const [controlsNote, setControlsNote] = useState<string | null>(null);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        workspaceResponse,
        controlsResponse,
        checklistResponse,
        icpResponse,
        offerResponse,
      ] = await Promise.all([
        getWorkspaceSettings(),
        getAdminControls(),
        getAdminSetupChecklist(),
        getICPProfiles(true),
        getOfferProfiles(true),
      ]);
      setWorkspace(workspaceResponse);
      setControls(controlsResponse);
      setChecklist(checklistResponse);
      setIcpProfiles(icpResponse.items);
      setOfferProfiles(offerResponse.items);
      setWorkspaceForm({
        workspace_name: workspaceResponse.workspace_name,
        company_name: workspaceResponse.company_name ?? "",
        company_website: workspaceResponse.company_website ?? "",
        default_language: workspaceResponse.default_language,
        default_tone: workspaceResponse.default_tone,
        default_icp_profile_id: workspaceResponse.default_icp_profile_id ?? "",
        default_offer_profile_id: workspaceResponse.default_offer_profile_id ?? "",
      });
      setControlsForm({
        allow_real_llm_calls: controlsResponse.allow_real_llm_calls,
        allow_real_email_drafts: controlsResponse.allow_real_email_drafts,
        allow_real_reply_reads: controlsResponse.allow_real_reply_reads,
        allow_real_dispatch: controlsResponse.allow_real_dispatch,
        dispatch_mode: controlsResponse.dispatch_mode,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  async function handleSaveWorkspace(event: React.FormEvent) {
    event.preventDefault();
    setWorkspaceSaving(true);
    setWorkspaceError(null);
    setWorkspaceNote(null);
    try {
      const updated = await updateWorkspaceSettings({
        workspace_name: workspaceForm.workspace_name,
        company_name: workspaceForm.company_name || null,
        company_website: workspaceForm.company_website || null,
        default_language: workspaceForm.default_language || null,
        default_tone: workspaceForm.default_tone || null,
        default_icp_profile_id: workspaceForm.default_icp_profile_id || null,
        default_offer_profile_id: workspaceForm.default_offer_profile_id || null,
      });
      setWorkspace(updated);
      setWorkspaceNote("Workspace Settings gespeichert.");
    } catch (err) {
      setWorkspaceError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setWorkspaceSaving(false);
    }
  }

  async function handleSaveControls(event: React.FormEvent) {
    event.preventDefault();
    setControlsSaving(true);
    setControlsError(null);
    setControlsNote(null);
    try {
      const updated = await updateAdminControls(controlsForm);
      setControls(updated);
      setControlsNote("Admin Controls gespeichert.");
    } catch (err) {
      setControlsError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setControlsSaving(false);
    }
  }

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Admin Controls</h1>
          <p className="mt-1 text-sm text-slate-600">
            Steuert Workspace-Defaults und sichere Standardwerte. Diese Einstellungen
            ersetzen keine Environment-Konfiguration — echte Provider bleiben nur
            aktiv, wenn zusätzlich die passenden Umgebungsvariablen gesetzt sind.
          </p>
        </div>

        <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
          <ul className="list-inside list-disc space-y-1">
            <li>Human Review und Do-not-contact können hier nicht deaktiviert werden.</li>
            <li>Real Dispatch/Manual Send erfordern zusätzlich die Environment-Aktivierung.</li>
            <li>Keine Secrets, API Keys oder Tokens werden hier je angezeigt.</li>
            <li>Mock Provider bleibt Standard.</li>
          </ul>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Wird geladen…</p>
        ) : error ? (
          <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
            {error}
          </div>
        ) : (
          <>
            <Card title="Workspace Settings">
              <form className="space-y-4" onSubmit={handleSaveWorkspace}>
                <Input
                  label="Workspace Name"
                  value={workspaceForm.workspace_name}
                  onChange={(e) =>
                    setWorkspaceForm({ ...workspaceForm, workspace_name: e.target.value })
                  }
                />
                <div className="grid gap-4 sm:grid-cols-2">
                  <Input
                    label="Company Name"
                    value={workspaceForm.company_name}
                    onChange={(e) =>
                      setWorkspaceForm({ ...workspaceForm, company_name: e.target.value })
                    }
                  />
                  <Input
                    label="Company Website"
                    value={workspaceForm.company_website}
                    onChange={(e) =>
                      setWorkspaceForm({ ...workspaceForm, company_website: e.target.value })
                    }
                  />
                  <Input
                    label="Default Language"
                    value={workspaceForm.default_language}
                    onChange={(e) =>
                      setWorkspaceForm({ ...workspaceForm, default_language: e.target.value })
                    }
                  />
                  <Input
                    label="Default Tone"
                    value={workspaceForm.default_tone}
                    onChange={(e) =>
                      setWorkspaceForm({ ...workspaceForm, default_tone: e.target.value })
                    }
                  />
                  <Select
                    label="Default ICP Profile"
                    value={workspaceForm.default_icp_profile_id}
                    options={[
                      { value: "", label: "Keins" },
                      ...icpProfiles.map((p) => ({ value: p.id, label: p.name })),
                    ]}
                    onChange={(e) =>
                      setWorkspaceForm({
                        ...workspaceForm,
                        default_icp_profile_id: e.target.value,
                      })
                    }
                  />
                  <Select
                    label="Default Offer Profile"
                    value={workspaceForm.default_offer_profile_id}
                    options={[
                      { value: "", label: "Keins" },
                      ...offerProfiles.map((p) => ({ value: p.id, label: p.name })),
                    ]}
                    onChange={(e) =>
                      setWorkspaceForm({
                        ...workspaceForm,
                        default_offer_profile_id: e.target.value,
                      })
                    }
                  />
                </div>
                <Button type="submit" loading={workspaceSaving}>
                  Workspace Settings speichern
                </Button>
                {workspaceError ? (
                  <p className="text-sm text-rose-400">{workspaceError}</p>
                ) : null}
                {workspaceNote ? <p className="text-sm text-slate-600">{workspaceNote}</p> : null}
              </form>
            </Card>

            {controls ? (
              <Card title="Admin Controls">
                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <Badge tone="positive">Human Review: Pflicht</Badge>
                  <Badge tone="positive">Do-not-contact: Pflicht</Badge>
                  <Badge tone={controls.real_llm_configured ? "warning" : "neutral"}>
                    LLM konfiguriert: {String(controls.real_llm_configured)}
                  </Badge>
                  <Badge tone={controls.email_integration_configured ? "warning" : "neutral"}>
                    Email Integration konfiguriert: {String(controls.email_integration_configured)}
                  </Badge>
                  <Badge tone={controls.reply_tracking_configured ? "warning" : "neutral"}>
                    Reply Tracking konfiguriert: {String(controls.reply_tracking_configured)}
                  </Badge>
                  <Badge tone={controls.real_send_env_enabled ? "negative" : "positive"}>
                    Real Send Env: {String(controls.real_send_env_enabled)}
                  </Badge>
                </div>
                <form className="space-y-4" onSubmit={handleSaveControls}>
                  <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">
                    Die folgenden Optionen wirken nur, wenn zusätzlich die passende
                    Environment-Variable gesetzt ist. Ohne Environment-Aktivierung
                    bleibt der jeweilige Provider im Mock/Safe Mode.
                  </div>
                  <label className="flex items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                      checked={controlsForm.allow_real_llm_calls}
                      onChange={(e) =>
                        setControlsForm({
                          ...controlsForm,
                          allow_real_llm_calls: e.target.checked,
                        })
                      }
                    />
                    Real LLM Calls erlauben
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                      checked={controlsForm.allow_real_email_drafts}
                      onChange={(e) =>
                        setControlsForm({
                          ...controlsForm,
                          allow_real_email_drafts: e.target.checked,
                        })
                      }
                    />
                    Real Email Drafts erlauben
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-700">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                      checked={controlsForm.allow_real_reply_reads}
                      onChange={(e) =>
                        setControlsForm({
                          ...controlsForm,
                          allow_real_reply_reads: e.target.checked,
                        })
                      }
                    />
                    Real Reply Reads erlauben
                  </label>
                  <label className="flex items-center gap-2 text-sm font-medium text-rose-200">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-rose-400/30 text-rose-400 focus:ring-rose-500"
                      checked={controlsForm.allow_real_dispatch}
                      onChange={(e) =>
                        setControlsForm({
                          ...controlsForm,
                          allow_real_dispatch: e.target.checked,
                        })
                      }
                    />
                    Real Dispatch erlauben (nur wirksam mit
                    OUTREACH_DISPATCH_ENABLE_REAL_SEND=true)
                  </label>
                  <Select
                    label="Dispatch Mode"
                    value={controlsForm.dispatch_mode}
                    options={[
                      { value: "draft_only", label: "Draft-only (sicher)" },
                      { value: "manual_send", label: "Manual Send (nur mit Real Send Env)" },
                    ]}
                    onChange={(e) =>
                      setControlsForm({
                        ...controlsForm,
                        dispatch_mode: e.target.value as "draft_only" | "manual_send",
                      })
                    }
                  />
                  <Button type="submit" loading={controlsSaving}>
                    Admin Controls speichern
                  </Button>
                  {controlsError ? (
                    <p className="text-sm text-rose-400">{controlsError}</p>
                  ) : null}
                  {controlsNote ? (
                    <p className="text-sm text-slate-600">{controlsNote}</p>
                  ) : null}
                </form>
                {controls.warnings.length > 0 ? (
                  <div className="mt-3 rounded-lg border border-amber-400/25 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
                    {controls.warnings.map((w) => (
                      <p key={w}>{w}</p>
                    ))}
                  </div>
                ) : null}
              </Card>
            ) : null}

            {checklist ? (
              <Card title="Setup Checklist">
                <div className="space-y-2">
                  {checklist.items.map((item) => (
                    <div
                      key={item.key}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 px-3 py-2"
                    >
                      <span className="text-sm text-slate-900">{item.label}</span>
                      <div className="flex items-center gap-2">
                        <Badge tone={CHECKLIST_TONE[item.status]}>{item.status}</Badge>
                        {item.detail ? (
                          <span className="text-xs text-slate-500">{item.detail}</span>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            ) : null}
          </>
        )}
      </div>
    </RequireAuth>
  );
}
