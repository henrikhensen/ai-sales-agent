"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ApiError, getLeadReplies, syncDraftReplies } from "@/lib/api";
import { canSyncReplies } from "@/lib/roles";
import type { Reply } from "@/lib/types";

interface DraftReplySyncActionProps {
  emailDraftId: string;
  leadId: string | null;
}

// Only ever reads/syncs replies for this draft — there is no reply/send
// button here or anywhere in this integration.
export function DraftReplySyncAction({ emailDraftId, leadId }: DraftReplySyncActionProps) {
  const { currentUser } = useAuth();
  const canSync = canSyncReplies(currentUser);

  const [replies, setReplies] = useState<Reply[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadReplies = useCallback(async () => {
    if (!leadId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const response = await getLeadReplies(leadId);
      setReplies(response.items.filter((reply) => reply.email_draft_id === emailDraftId));
    } catch {
      // Non-fatal: the sync button below still works even if this initial
      // lookup fails.
    } finally {
      setLoading(false);
    }
  }, [leadId, emailDraftId]);

  useEffect(() => {
    loadReplies();
  }, [loadReplies]);

  async function handleSync() {
    setSyncing(true);
    setError(null);
    setMessage(null);
    try {
      const result = await syncDraftReplies(emailDraftId);
      setMessage(result.message);
      await loadReplies();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setSyncing(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500">Lade Reply-Status…</p>;
  }

  return (
    <div className="space-y-2">
      <p className="text-sm">
        <Badge tone={replies.length > 0 ? "info" : "neutral"}>
          {replies.length} {replies.length === 1 ? "Reply" : "Replies"}
        </Badge>
      </p>
      {canSync ? (
        <>
          <Button variant="secondary" onClick={handleSync} loading={syncing}>
            Replies für diesen Draft synchronisieren
          </Button>
          {message ? <p className="text-xs text-emerald-200">{message}</p> : null}
          {error ? <p className="text-xs text-rose-400">{error}</p> : null}
        </>
      ) : null}
    </div>
  );
}
