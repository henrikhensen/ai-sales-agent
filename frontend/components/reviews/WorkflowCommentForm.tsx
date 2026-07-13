"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { ApiError, addWorkflowReviewComment } from "@/lib/api";
import type { WorkflowCommentResponse } from "@/lib/types";

interface WorkflowCommentFormProps {
  workflowId: string;
  onAdded?: (result: WorkflowCommentResponse) => void;
}

export function WorkflowCommentForm({ workflowId, onAdded }: WorkflowCommentFormProps) {
  const [reviewerName, setReviewerName] = useState("");
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      const result = await addWorkflowReviewComment(workflowId, {
        reviewer_name: reviewerName.trim() || undefined,
        comment: comment.trim(),
      });
      setSuccess(true);
      setComment("");
      onAdded?.(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="space-y-3" onSubmit={handleSubmit}>
      <p className="text-sm text-slate-600">
        <strong>
          Kommentare und Review Status lösen keine Kontaktaufnahme aus.
        </strong>
      </p>
      <Input
        label="Reviewer Name"
        value={reviewerName}
        onChange={(e) => setReviewerName(e.target.value)}
        placeholder="z. B. Henrik"
      />
      <Textarea
        label="Kommentar *"
        required
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="z. B. Bitte Nutzenargument prüfen."
      />
      <Button type="submit" loading={saving}>
        Kommentar speichern
      </Button>
      {success ? (
        <p className="text-sm text-emerald-200">Kommentar wurde gespeichert.</p>
      ) : null}
      {error ? (
        <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
          {error}
        </div>
      ) : null}
    </form>
  );
}
