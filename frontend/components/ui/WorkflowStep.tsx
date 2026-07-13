interface WorkflowStepProps {
  index: number;
  title: string;
  description: string;
}

/** One numbered step in a linear workflow explainer (e.g. the home page's
 * "So funktioniert's" section) — large index numeral, short title, one
 * supporting sentence. */
export function WorkflowStep({ index, title, description }: WorkflowStepProps) {
  return (
    <div className="group relative flex flex-col gap-3 rounded-3xl border border-slate-200/70 bg-white p-6 shadow-premium transition-transform hover:-translate-y-0.5">
      <span className="text-3xl font-bold tracking-tight text-brand-500/90">
        {String(index).padStart(2, "0")}
      </span>
      <p className="text-sm font-semibold text-slate-900">{title}</p>
      <p className="text-xs leading-relaxed text-slate-600">{description}</p>
    </div>
  );
}
