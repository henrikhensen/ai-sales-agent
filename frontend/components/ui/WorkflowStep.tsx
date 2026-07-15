import type { ReactNode } from "react";

interface WorkflowStepProps {
  index: number;
  title: string;
  description: string;
  /** Optional larger visual area (an abstract SVG/icon, never a photo) —
   * used by the home page's Workflow-Showcase, where each step gets a
   * "große visuelle Fläche" per the brief. Omitted entirely elsewhere, so
   * every existing/compact use of this component is unaffected. */
  visual?: ReactNode;
}

/** One topic in a genuine ordered pipeline — a large, sharp-edged block
 * that flips to a solid `muted` fill on hover/focus. The invert is this
 * design's signature interaction: every topic literally turns the process
 * into a contrast statement, echoing the hero's own bold typography
 * instead of decorating the card with a color or icon. A small index
 * numeral is honest, not decorative — kept quiet in the corner rather than
 * the focal element. */
export function WorkflowStep({ index, title, description, visual }: WorkflowStepProps) {
  return (
    <div
      tabIndex={0}
      className="group relative flex min-h-[13rem] flex-col justify-between border border-muted/25 bg-surface p-6 text-muted outline-none transition-colors duration-150 hover:bg-muted hover:text-canvas focus-visible:bg-muted focus-visible:text-canvas"
    >
      <div className="flex items-start justify-between gap-4">
        <span className="mono-label text-muted/40 transition-colors duration-150 group-hover:text-canvas/60 group-focus-visible:text-canvas/60">
          {String(index).padStart(2, "0")}
        </span>
        {visual ? (
          <span className="text-muted/50 transition-colors duration-150 group-hover:text-canvas/60 group-focus-visible:text-canvas/60">
            {visual}
          </span>
        ) : null}
      </div>
      <div>
        <p className="text-lg font-bold leading-snug tracking-tight">{title}</p>
        <p className="mt-2 text-sm leading-relaxed text-muted/60 transition-colors duration-150 group-hover:text-canvas/70 group-focus-visible:text-canvas/70">
          {description}
        </p>
      </div>
    </div>
  );
}
