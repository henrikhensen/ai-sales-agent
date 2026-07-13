interface WorkflowStepProps {
  index: number;
  title: string;
  description: string;
}

/** One topic in the core workflow (e.g. the home page's "Core Workflow"
 * section) — a large, sharp-edged block that flips to a solid `muted`
 * fill on hover/focus. The invert is this design's signature
 * interaction: every topic literally turns the process into a contrast
 * statement, echoing the hero's own bold typography instead of
 * decorating the card with a color or icon. Genuinely sequential (this is
 * a real five-step pipeline), so a small index numeral is honest, not
 * decorative — kept quiet in the corner rather than the focal element. */
export function WorkflowStep({ index, title, description }: WorkflowStepProps) {
  return (
    <div
      tabIndex={0}
      className="group relative flex min-h-[13rem] flex-col justify-between border border-muted/25 bg-surface p-6 text-muted outline-none transition-colors duration-150 hover:bg-muted hover:text-canvas focus-visible:bg-muted focus-visible:text-canvas"
    >
      <span className="mono-label text-muted/40 transition-colors duration-150 group-hover:text-canvas/60 group-focus-visible:text-canvas/60">
        {String(index).padStart(2, "0")}
      </span>
      <div>
        <p className="text-lg font-bold leading-snug tracking-tight">{title}</p>
        <p className="mt-2 text-sm leading-relaxed text-muted/60 transition-colors duration-150 group-hover:text-canvas/70 group-focus-visible:text-canvas/70">
          {description}
        </p>
      </div>
    </div>
  );
}
