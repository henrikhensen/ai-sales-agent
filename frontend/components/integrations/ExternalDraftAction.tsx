"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Button } from "@/components/ui/Button";
import {
  ApiError,
  createExternalEmailDraft,
  getExternalEmailDraftStatus,
} from "@/lib/api";
import { canCreateExternalEmailDraft } from "@/lib/roles";
import type { ExternalEmailDraft } from "@/lib/types";

const STATUS_LABELS: Record<string, string> = {
  mock_created: "Mock Draft erstellt",
  created: "Draft erstellt",
  blocked: "Blockiert",
  failed: "Fehlgeschlagen",
};

interface ExternalDraftActionProps {
  emailDraftId: string;
}

// Deliberately named "Externen Draft erstellen" everywhere — never "Senden"
// / "Send" / "Email senden" / "Outreach starten". This action can only ever
// create a draft at Gmail/Outlook/Mock; there is no send capability here.
export function ExternalDraftAction({ emailDraftId }: ExternalDraftActionProps) {
  const { currentUser } = useAuth();
  const canCreate = canCreateExternalEmailDraft(currentUser);

  const [existing, setExisting] = useState<ExternalEmailDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [blockMessage, setBlockMessage] = useState<string | null>(null);

  const loadStatus = useCallback(async () => {
    setLoading(true);
    try {
      const status = await getExternalEmailDraftStatus(emailDraftId);
      setExisting(status.external_draft);
    } catch {
      // Non-fatal: the create button below still works even if this
      // initial status lookup fails.
    } finally {
      setLoading(false);
    }
  }, [emailDraftId]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  async function handleCreate() {
    setCreating(true);
    setError(null);
    setBlockMessage(null);
    try {
      const result = await createExternalEmailDraft(emailDraftId);
      setExisting(result.external_draft);
      if (result.blocked) {
        setBlockMessage(result.message);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setCreating(false);
    }
  }

  if (loading) {
    return <p className="text-sm text-slate-500">Lade externen Draft-Status…</p>;
  }

  return (
    <div className="space-y-2">
      {existing ? (
        <div className="text-sm">
          <p>
            <span className="font-medium">{existing.provider}</span>
            {" — "}
            {STATUS_LABELS[existing.provider_status] ?? existing.provider_status}
          </p>
          {existing.provider_draft_url ? (
            <a
              href={existing.provider_draft_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-600 hover:text-brand-700"
            >
              Draft öffnen →
            </a>
          ) : null}
          {existing.last_error ? (
            <p className="mt-1 text-xs text-rose-400">{existing.last_error}</p>
          ) : null}
        </div>
      ) : (
        <p className="text-sm text-slate-500">Noch kein externer Draft erstellt.</p>
      )}

      {canCreate ? (
        <>
          <Button variant="secondary" onClick={handleCreate} loading={creating}>
            Externen Draft erstellen
          </Button>
          {blockMessage ? (
            <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
              {blockMessage}
            </div>
          ) : null}
          {error ? <p className="text-xs text-rose-400">{error}</p> : null}
        </>
      ) : (
        <p className="text-xs text-slate-500">
          Nur Admin- und Sales-Konten dürfen externe Drafts erstellen.
        </p>
      )}
    </div>
  );
}
