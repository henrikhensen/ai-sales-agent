interface WorkflowStepProps {
  index: number;
  title: string;
  description: string;
}

/** One topic in the core workflow (e.g. the home page's "Core Workflow"
 * section) — a large, sharp-edged block that flips to a solid black
 * fill on hover/focus. The black/white invert is this design's signature
 * interaction: every topic literally turns the process into a contrast
 * statement, echoing the hero's own black-on-white typography instead of
 * decorating the card with a color or icon. Genuinely sequential (this is
 * a real five-step pipeline), so a small index numeral is honest, not
 * decorative — kept quiet in the corner rather than the focal element. */
export function WorkflowStep({ index, title, description }: WorkflowStepProps) {
  return (
    <div
      tabIndex={0}
      className="group relative flex min-h-[13rem] flex-col justify-between border border-ink-950 bg-white p-6 text-ink-950 outline-none transition-colors duration-150 hover:bg-ink-950 hover:text-white focus-visible:bg-ink-950 focus-visible:text-white"
    >
      <span className="mono-label text-ink-400 transition-colors duration-150 group-hover:text-white/50 group-focus-visible:text-white/50">
        {String(index).padStart(2, "0")}
      </span>
      <div>
        <p className="text-lg font-bold leading-snug tracking-tight">{title}</p>
        <p className="mt-2 text-sm leading-relaxed text-ink-500 transition-colors duration-150 group-hover:text-white/70 group-focus-visible:text-white/70">
          {description}
        </p>
      </div>
    </div>
  );
}
