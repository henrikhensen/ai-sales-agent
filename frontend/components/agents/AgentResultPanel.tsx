import type { ReactNode } from "react";

import { Card } from "@/components/ui/Card";
import { JsonViewer } from "@/components/ui/JsonViewer";

interface AgentResultPanelProps<T> {
  loading: boolean;
  error: string | null;
  result: T | null;
  emptyHint?: string;
  renderSummary?: (result: T) => ReactNode;
}

export function AgentResultPanel<T>({
  loading,
  error,
  result,
  emptyHint,
  renderSummary,
}: AgentResultPanelProps<T>) {
  return (
    <Card title="Ergebnis">
      {loading ? (
        <p className="text-sm text-slate-500">Anfrage läuft…</p>
      ) : error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      ) : result ? (
        <div className="space-y-4">
          {renderSummary ? renderSummary(result) : null}
          <details open={!renderSummary}>
            <summary className="cursor-pointer text-sm font-medium text-slate-600">
              Rohdaten (JSON)
            </summary>
            <div className="mt-2">
              <JsonViewer data={result} />
            </div>
          </details>
        </div>
      ) : (
        <p className="text-sm text-slate-500">
          {emptyHint ?? "Noch keine Anfrage gesendet."}
        </p>
      )}
    </Card>
  );
}
