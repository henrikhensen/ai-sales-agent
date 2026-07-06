"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { ApiError, updateEmailDraftReviewStatus } from "@/lib/api";
import type { EmailDraftReviewStatus, EmailDraftReviewStatusResponse } from "@/lib/types";
import { EMAIL_REVIEW_STATUS_OPTIONS } from "./ReviewStatusBadge";

interface ReviewStatusFormProps {
  emailDraftId: string;
  currentStatus: EmailDraftReviewStatus;
  onUpdated?: (result: EmailDraftReviewStatusResponse) => void;
}

export function ReviewStatusForm({
  emailDraftId,
  currentStatus,
  onUpdated,
}: ReviewStatusFormProps) {
  const [status, setStatus] = useState<EmailDraftReviewStatus>(currentStatus);
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
      const result = await updateEmailDraftReviewStatus(emailDraftId, {
        review_status: status,
        reviewer_name: reviewerName.trim() || undefined,
        comment: comment.trim() || undefined,
      });
      setSuccess(true);
      onUpdated?.(result);
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
          Approval ist nur interne Prüfung. Es wird keine E-Mail gesendet.
        </strong>
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <Select
          label="Review Status"
          value={status}
          options={EMAIL_REVIEW_STATUS_OPTIONS}
          onChange={(e) => setStatus(e.target.value as EmailDraftReviewStatus)}
        />
        <Input
          label="Reviewer Name"
          value={reviewerName}
          onChange={(e) => setReviewerName(e.target.value)}
          placeholder="z. B. Henrik"
        />
      </div>
      <Textarea
        label="Kommentar"
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Optionaler Kommentar zur Prüfung…"
      />
      <Button type="submit" loading={saving}>
        Speichern
      </Button>
      {success ? (
        <p className="text-sm text-emerald-700">Review Status wurde gespeichert.</p>
      ) : null}
      {error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      ) : null}
    </form>
  );
}
