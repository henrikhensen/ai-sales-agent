"use client";

import { useCallback, useEffect, useState } from "react";

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
  QualityEntityType,
  QualityFeedback,
  QualityFeedbackType,
} from "@/lib/types";

const ENTITY_TYPES: QualityEntityType[] = [
  "lead_candidate",
  "crm_lead",
  "company",
  "email_draft",
  "workflow_run",
  "outreach_queue_item",
  "dispatch",
  "reply",
  "qualification_result",
];

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
  const { currentUser } = useAuth();
  const [items, setItems] = useState<QualityFeedback[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);

  const [form, setForm] = useState({
    entity_type: "email_draft" as QualityEntityType,
    entity_id: "",
    rating: "3",
    feedback_type: "quality_issue" as QualityFeedbackType,
    feedback_text: "",
    is_blocking: false,
  });
  const [creating, setCreating] = useState(false);

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
        entity_id: form.entity_id,
        rating: Number(form.rating),
        feedback_type: form.feedback_type,
        feedback_text: form.feedback_text || null,
        is_blocking: form.is_blocking,
      });
      setForm({ ...form, entity_id: "", feedback_text: "", is_blocking: false });
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
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {actionError}
          </div>
        ) : null}

        <Card title="Feedback geben">
          <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleCreate}>
            <Select
              label="Entity Type"
              value={form.entity_type}
              options={ENTITY_TYPES.map((t) => ({ value: t, label: t }))}
              onChange={(e) =>
                setForm({ ...form, entity_type: e.target.value as QualityEntityType })
              }
            />
            <Input
              label="Entity ID"
              value={form.entity_id}
              onChange={(e) => setForm({ ...form, entity_id: e.target.value })}
              required
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
                <span className="ml-3 text-sm text-emerald-700">Feedback gespeichert.</span>
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
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
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
                      <span className="ml-2 text-slate-500">{item.entity_id}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {item.is_blocking ? <Badge tone="negative">blockierend</Badge> : null}
                      <Badge tone={REVIEW_STATUS_TONE[item.review_status] ?? "neutral"}>
                        {item.review_status}
                      </Badge>
                    </div>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {item.feedback_type} · Bewertung {item.rating}/5 ·{" "}
                    {new Date(item.created_at).toLocaleString("de-DE")}
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
