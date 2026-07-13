"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { RequireAuth } from "@/components/auth/RequireAuth";
import { QualityScoreBadge } from "@/components/quality/QualityScoreBadge";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import {
  ApiError,
  archiveReply,
  getReplies,
  markReplyRead,
  syncRecentReplies,
} from "@/lib/api";
import { canSyncReplies } from "@/lib/roles";
import type { Reply, ReplyCategory, ReplySentiment } from "@/lib/types";

function formatDate(value: string): string {
  return new Date(value).toLocaleString("de-DE");
}

const CATEGORY_TONE: Record<string, "positive" | "negative" | "warning" | "info" | "neutral"> = {
  interested: "positive",
  meeting_request: "positive",
  needs_more_info: "info",
  not_interested: "negative",
  unsubscribe: "negative",
  out_of_office: "neutral",
  unknown: "neutral",
};

const CATEGORY_OPTIONS = [
  { value: "", label: "Alle Kategorien" },
  { value: "interested", label: "Interested" },
  { value: "not_interested", label: "Not interested" },
  { value: "needs_more_info", label: "Needs more info" },
  { value: "meeting_request", label: "Meeting request" },
  { value: "out_of_office", label: "Out of office" },
  { value: "unsubscribe", label: "Unsubscribe" },
  { value: "unknown", label: "Unknown" },
];

const SENTIMENT_OPTIONS = [
  { value: "", label: "Alle Sentiments" },
  { value: "positive", label: "Positive" },
  { value: "neutral", label: "Neutral" },
  { value: "negative", label: "Negative" },
  { value: "unclear", label: "Unclear" },
];

const READ_OPTIONS = [
  { value: "", label: "Gelesen: egal" },
  { value: "false", label: "Ungelesen" },
  { value: "true", label: "Gelesen" },
];

const ARCHIVED_OPTIONS = [
  { value: "false", label: "Aktiv" },
  { value: "true", label: "Archiviert" },
  { value: "", label: "Alle" },
];

interface ReplyRowProps {
  reply: Reply;
  onChanged: () => void;
}

function ReplyRow({ reply, onChanged }: ReplyRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleMarkRead() {
    setBusy(true);
    setError(null);
    try {
      await markReplyRead(reply.id, !reply.is_read);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusy(false);
    }
  }

  async function handleArchive() {
    setBusy(true);
    setError(null);
    try {
      await archiveReply(reply.id, !reply.is_archived);
      onChanged();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className={`rounded-lg border px-4 py-3 ${
        reply.is_read ? "border-slate-200 bg-surface" : "border-brand-200 bg-brand-50/40"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-slate-900">
            {reply.from_name ? `${reply.from_name} <${reply.from_email}>` : reply.from_email}
          </p>
          <p className="text-sm text-slate-700">{reply.subject ?? "(kein Betreff)"}</p>
          <p className="mt-1 text-xs text-slate-500">{formatDate(reply.received_at)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {reply.reply_category ? (
            <Badge tone={CATEGORY_TONE[reply.reply_category] ?? "neutral"}>
              {reply.reply_category}
            </Badge>
          ) : null}
          {reply.sentiment ? <Badge tone="neutral">{reply.sentiment}</Badge> : null}
          <Badge tone="info">{reply.provider}</Badge>
          {!reply.is_read ? <Badge tone="warning">ungelesen</Badge> : null}
          {reply.is_archived ? <Badge tone="neutral">archiviert</Badge> : null}
        </div>
      </div>

      <p className="mt-2 text-sm text-slate-600">{reply.body_preview}</p>

      {reply.compliance_warning ? (
        <div className="mt-2 rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-xs text-rose-200">
          {reply.compliance_warning}
        </div>
      ) : null}

      {expanded ? (
        <div className="mt-3 space-y-1 border-t border-slate-100 pt-3 text-xs text-slate-600">
          <div className="pb-1">
            <QualityScoreBadge entityType="reply" entityId={reply.id} />
          </div>
          <p>Confidence: {reply.confidence_score ?? "—"}</p>
          <p>Detected intent: {reply.detected_intent ?? "—"}</p>
          {reply.recommended_pipeline_status ? (
            <p>
              Empfohlener Pipeline-Status: <strong>{reply.recommended_pipeline_status}</strong>{" "}
              (wird nicht automatisch gesetzt)
            </p>
          ) : null}
          {reply.provider_message_url ? (
            <p>
              <a
                className="text-brand-600 underline"
                href={reply.provider_message_url}
                target="_blank"
                rel="noreferrer"
              >
                Nachricht beim Provider öffnen
              </a>
            </p>
          ) : null}
          {reply.lead_id ? (
            <p>
              <Link className="text-brand-600 underline" href={`/crm/pipeline`}>
                Zur Pipeline
              </Link>
            </p>
          ) : null}
        </div>
      ) : null}

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button variant="ghost" onClick={() => setExpanded((v) => !v)}>
          {expanded ? "Weniger" : "Details"}
        </Button>
        <Button variant="secondary" onClick={handleMarkRead} loading={busy}>
          {reply.is_read ? "Als ungelesen markieren" : "Als gelesen markieren"}
        </Button>
        <Button variant="ghost" onClick={handleArchive} loading={busy}>
          {reply.is_archived ? "Dearchivieren" : "Archivieren"}
        </Button>
        {error ? <span className="text-xs text-rose-400">{error}</span> : null}
      </div>
    </div>
  );
}

export default function RepliesPage() {
  const { currentUser } = useAuth();
  const canSync = canSyncReplies(currentUser);

  const [replies, setReplies] = useState<Reply[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [category, setCategory] = useState("");
  const [sentiment, setSentiment] = useState("");
  const [isRead, setIsRead] = useState("");
  const [isArchived, setIsArchived] = useState("false");

  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getReplies({
        category: category as ReplyCategory | undefined || undefined,
        sentiment: sentiment as ReplySentiment | undefined || undefined,
        is_read: isRead === "" ? undefined : isRead === "true",
        is_archived: isArchived === "" ? undefined : isArchived === "true",
      });
      setReplies(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, [category, sentiment, isRead, isArchived]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSyncRecent() {
    setSyncing(true);
    setSyncMessage(null);
    setSyncError(null);
    try {
      const result = await syncRecentReplies();
      setSyncMessage(result.message);
      await load();
    } catch (err) {
      setSyncError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <RequireAuth>
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Reply Inbox</h1>
          <p className="mt-1 text-sm text-slate-600">
            Antworten aus Gmail/Outlook/Mock — nur lesen und verwalten, nie senden.
          </p>
        </div>

        <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
          <ul className="list-inside list-disc space-y-1">
            <li>Reply Tracking liest nur Antworten, wenn aktiv und autorisiert.</li>
            <li>Mock Provider nutzt Testdaten.</li>
            <li>Es werden keine automatischen Antworten gesendet.</li>
            <li>Es gibt keinen Send Button.</li>
            <li>Do-not-contact Signale werden markiert.</li>
            <li>Unsubscribe Antworten müssen respektiert werden.</li>
          </ul>
        </div>

        <Card title="Filter">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Select
              label="Kategorie"
              options={CATEGORY_OPTIONS}
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            />
            <Select
              label="Sentiment"
              options={SENTIMENT_OPTIONS}
              value={sentiment}
              onChange={(e) => setSentiment(e.target.value)}
            />
            <Select
              label="Gelesen"
              options={READ_OPTIONS}
              value={isRead}
              onChange={(e) => setIsRead(e.target.value)}
            />
            <Select
              label="Archiviert"
              options={ARCHIVED_OPTIONS}
              value={isArchived}
              onChange={(e) => setIsArchived(e.target.value)}
            />
          </div>
        </Card>

        {canSync ? (
          <div className="flex flex-wrap items-center gap-3">
            <Button onClick={handleSyncRecent} loading={syncing}>
              Recent Replies synchronisieren
            </Button>
            {syncMessage ? (
              <span className="text-sm text-emerald-200">{syncMessage}</span>
            ) : null}
            {syncError ? <span className="text-sm text-rose-400">{syncError}</span> : null}
          </div>
        ) : null}

        <Card title="Replies">
          {loading ? (
            <p className="text-sm text-slate-500">Replies werden geladen…</p>
          ) : error ? (
            <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </div>
          ) : replies && replies.length > 0 ? (
            <div className="space-y-3">
              {replies.map((reply) => (
                <ReplyRow key={reply.id} reply={reply} onChanged={load} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">Keine Replies vorhanden.</p>
          )}
        </Card>
      </div>
    </RequireAuth>
  );
}
