"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import {
  ApiError,
  archiveQualityFeedback,
  createQualityFeedback,
  getQualityFeedback,
  reviewQualityFeedback,
} from "@/lib/api";
import { canReviewQualityFeedback, canViewQuality } from "@/lib/roles";
import type {
  FeedbackEntityType,
  QualityFeedback,
  QualityFeedbackPriority,
  QualityFeedbackType,
} from "@/lib/types";

const ENTITY_TYPES: { value: FeedbackEntityType; label: string }[] = [
  { value: "general", label: "Allgemein / UI (kein bestimmter Datensatz)" },
  { value: "lead_candidate", label: "lead_candidate" },
  { value: "crm_lead", label: "crm_lead" },
  { value: "company", label: "company" },
  { value: "email_draft", label: "email_draft" },
  { value: "workflow_run", label: "workflow_run" },
  { value: "real_world_test_run", label: "real_world_test_run" },
  { value: "outreach_queue_item", label: "outreach_queue_item" },
  { value: "dispatch", label: "dispatch" },
  { value: "reply", label: "reply" },
  { value: "qualification_result", label: "qualification_result" },
];

const PRIORITIES: QualityFeedbackPriority[] = ["low", "medium", "high"];

const PRIORITY_TONE: Record<string, "positive" | "warning" | "negative" | "neutral" | "info"> = {
  low: "neutral",
  medium: "info",
  high: "warning",
};

const FEEDBACK_TYPES: QualityFeedbackType[] = [
  "positive",
  "negative",
  "correction",
  "bug",
  "quality_issue",
  "compliance_issue",
  "missing_context",
  "wrong_target",
  "bad_copy",
  "good_result",
];

const REVIEW_STATUS_TONE: Record<string, "positive" | "warning" | "negative" | "neutral"> = {
  open: "neutral",
  reviewed: "warning",
  accepted: "positive",
  rejected: "negative",
  archived: "neutral",
};

export default function QualityFeedbackPage() {
  return (
    <Suspense fallback={null}>
      <QualityFeedbackPageContent />
    </Suspense>
  );
}

function QualityFeedbackPageContent() {
  const { currentUser } = useAuth();
  const searchParams = useSearchParams();
  const [items, setItems] = useState<QualityFeedback[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const [form, setForm] = useState(() => ({
    entity_type: (searchParams.get("entity_type") as FeedbackEntityType) || "email_draft",
    entity_id: searchParams.get("entity_id") || "",
    rating: "3",
    feedback_type: "quality_issue" as QualityFeedbackType,
    priority: "medium" as QualityFeedbackPriority,
    feedback_text: "",
    is_blocking: false,
    real_world_test_run_id: searchParams.get("real_world_test_run_id") || "",
  }));
  const [creating, setCreating] = useState(false);
  const isGeneral = form.entity_type === "general";

  const canView = canViewQuality(currentUser);
  const canReview = canReviewQualityFeedback(currentUser);

  const load = useCallback(async () => {
    if (!canView) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await getQualityFeedback({ limit: 100 });
      setItems(result.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, [canView]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    setCreating(true);
    setActionError(null);
    setSubmitted(false);
    try {
      await createQualityFeedback({
        entity_type: form.entity_type,
        entity_id: isGeneral ? null : form.entity_id,
        rating: Number(form.rating),
        feedback_type: form.feedback_type,
        priority: form.priority,
        feedback_text: form.feedback_text || null,
        is_blocking: form.is_blocking,
        real_world_test_run_id: form.real_world_test_run_id || null,
      });
      setForm({
        ...form,
        entity_id: "",
        feedback_text: "",
        is_blocking: false,
        real_world_test_run_id: "",
      });
      setSubmitted(true);
      if (canView) {
        await load();
      }
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setCreating(false);
    }
  }

  async function handleReview(feedbackId: string, status: "reviewed" | "accepted" | "rejected") {
    setBusyId(feedbackId);
    setActionError(null);
    try {
      await reviewQualityFeedback(feedbackId, { review_status: status });
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleArchive(feedbackId: string) {
    setBusyId(feedbackId);
    setActionError(null);
    try {
      await archiveQualityFeedback(feedbackId);
      await load();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Quality Feedback</h1>
          <p className="mt-1 text-sm text-slate-600">
            Feedback zu einer Entität (z.B. Email Draft, Lead, Workflow Run). Feedback
            ändert nie automatisch etwas — kein Redraft, kein erneuter Versand, keine
            automatische Kontaktaufnahme.
          </p>
        </div>

        {actionError ? (
          <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
            {actionError}
          </div>
        ) : null}

        <Card title="Feedback geben">
          <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleCreate}>
            <Select
              label="Entity Type"
              value={form.entity_type}
              options={ENTITY_TYPES}
              onChange={(e) =>
                setForm({ ...form, entity_type: e.target.value as FeedbackEntityType })
              }
            />
            <Input
              label={isGeneral ? "Entity ID (nicht benötigt)" : "Entity ID"}
              value={form.entity_id}
              onChange={(e) => setForm({ ...form, entity_id: e.target.value })}
              disabled={isGeneral}
              required={!isGeneral}
            />
            <Select
              label="Bewertung (1-5)"
              value={form.rating}
              options={["1", "2", "3", "4", "5"].map((v) => ({ value: v, label: v }))}
              onChange={(e) => setForm({ ...form, rating: e.target.value })}
            />
            <Select
              label="Feedback Type"
              value={form.feedback_type}
              options={FEEDBACK_TYPES.map((t) => ({ value: t, label: t }))}
              onChange={(e) =>
                setForm({ ...form, feedback_type: e.target.value as QualityFeedbackType })
              }
            />
            <Select
              label="Priorität"
              value={form.priority}
              options={PRIORITIES.map((p) => ({ value: p, label: p }))}
              onChange={(e) =>
                setForm({ ...form, priority: e.target.value as QualityFeedbackPriority })
              }
              hint="Nur eine Einordnungshilfe für Reviewer — ändert nichts automatisch."
            />
            <Input
              label="Real-World Test Run ID (optional)"
              value={form.real_world_test_run_id}
              onChange={(e) => setForm({ ...form, real_world_test_run_id: e.target.value })}
            />
            <div className="sm:col-span-2">
              <Textarea
                label="Kommentar"
                value={form.feedback_text}
                onChange={(e) => setForm({ ...form, feedback_text: e.target.value })}
                maxLength={3000}
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input
                type="checkbox"
                checked={form.is_blocking}
                onChange={(e) => setForm({ ...form, is_blocking: e.target.checked })}
              />
              Blockierend (z.B. gravierendes Compliance- oder Qualitätsproblem)
            </label>
            <div className="sm:col-span-2">
              <Button type="submit" loading={creating}>
                Feedback senden
              </Button>
              {submitted ? (
                <span className="ml-3 text-sm text-emerald-200">Feedback gespeichert.</span>
              ) : null}
            </div>
          </form>
        </Card>

        {!canView ? (
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
            Feedback-Listen und Reviews sind Admin-, Sales- und Reviewer-Konten
            vorbehalten. Ihr Feedback wurde trotzdem gespeichert.
          </div>
        ) : loading ? (
          <p className="text-sm text-slate-500">Wird geladen…</p>
        ) : error ? (
          <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
            {error}
          </div>
        ) : (
          <Card title="Feedback-Liste">
            <div className="space-y-2">
              {items.length === 0 ? (
                <p className="text-sm text-slate-500">Noch kein Feedback.</p>
              ) : null}
              {items.map((item) => (
                <div key={item.id} className="rounded-lg border border-slate-200 px-3 py-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="text-sm">
                      <span className="font-semibold text-slate-900">
                        {item.entity_type}
                      </span>
                      {item.entity_id ? (
                        <span className="ml-2 text-slate-500">{item.entity_id}</span>
                      ) : null}
                    </div>
                    <div className="flex items-center gap-2">
                      {item.is_blocking ? <Badge tone="negative">blockierend</Badge> : null}
                      <Badge tone={PRIORITY_TONE[item.priority] ?? "neutral"}>
                        {item.priority}
                      </Badge>
                      <Badge tone={REVIEW_STATUS_TONE[item.review_status] ?? "neutral"}>
                        {item.review_status}
                      </Badge>
                    </div>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {item.feedback_type} · Bewertung {item.rating}/5 ·{" "}
                    {new Date(item.created_at).toLocaleString("de-DE")}
                    {item.real_world_test_run_id
                      ? ` · Test Run: ${item.real_world_test_run_id}`
                      : ""}
                  </p>
                  {item.feedback_text ? (
                    <p className="mt-1 text-sm text-slate-700">{item.feedback_text}</p>
                  ) : null}
                  {canReview && item.review_status === "open" ? (
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Button
                        variant="secondary"
                        loading={busyId === item.id}
                        onClick={() => handleReview(item.id, "accepted")}
                      >
                        Akzeptieren
                      </Button>
                      <Button
                        variant="secondary"
                        loading={busyId === item.id}
                        onClick={() => handleReview(item.id, "reviewed")}
                      >
                        Als geprüft markieren
                      </Button>
                      <Button
                        variant="ghost"
                        loading={busyId === item.id}
                        onClick={() => handleReview(item.id, "rejected")}
                      >
                        Ablehnen
                      </Button>
                      <Button
                        variant="ghost"
                        loading={busyId === item.id}
                        onClick={() => handleArchive(item.id)}
                      >
                        Archivieren
                      </Button>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </RequireAuth>
  );
}
