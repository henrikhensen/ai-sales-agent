import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

/** Centered placeholder for a section with no data yet — used instead of
 * a bare "keine Daten" line so empty runs/leads/queues still look like a
 * real product rather than an unfinished admin table. */
export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="border border-dashed border-ink-950/20 bg-bone px-6 py-12 text-center">
      <p className="text-sm font-semibold text-ink-950">{title}</p>
      {description ? <p className="mt-1 text-sm text-ink-500">{description}</p> : null}
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}
