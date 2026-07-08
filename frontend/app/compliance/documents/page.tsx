"use client";

import { useCallback, useEffect, useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { Card } from "@/components/ui/Card";
import { ApiError, getComplianceDocuments } from "@/lib/api";
import type { ComplianceDocumentsResponse } from "@/lib/types";

export default function ComplianceDocumentsPage() {
  const [data, setData] = useState<ComplianceDocumentsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getComplianceDocuments();
      setData(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <RequireRole
      allowedRoles={["admin", "sales", "reviewer"]}
      deniedMessage="Nur Admin-, Sales- und Reviewer-Konten haben Zugriff auf Compliance Documents."
    >
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Compliance Documents</h1>
          <p className="mt-1 text-sm text-slate-600">
            Vorlagen und Hinweise zur Vorbereitung auf eine rechtliche/Compliance-Prüfung.
          </p>
        </div>

        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          <p className="font-semibold">Keine Rechtsberatung.</p>
          <p className="mt-1">
            Diese Dokumente sind Vorlagen und Hinweise — keine Rechtsberatung und
            keine Zertifizierung der Compliance mit GDPR, CCPA oder anderen
            Gesetzen/Standards. Echte Nutzung erfordert eine eigene rechtliche
            Prüfung. Siehe auch{" "}
            <a href="/compliance/status" className="underline hover:no-underline">
              Compliance Status
            </a>
            .
          </p>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Wird geladen…</p>
        ) : error ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
            {error}
          </div>
        ) : data ? (
          <>
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
              {data.disclaimer}
            </div>
            <div className="space-y-4">
              {data.documents.map((doc) => (
                <Card key={doc.key} title={doc.title}>
                  <p className="whitespace-pre-line text-sm text-slate-700">{doc.body}</p>
                </Card>
              ))}
            </div>
          </>
        ) : null}
      </div>
    </RequireRole>
  );
}
