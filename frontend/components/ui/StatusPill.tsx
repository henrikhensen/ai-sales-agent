type StatusTone = "positive" | "warning" | "negative" | "neutral" | "info";

interface StatusPillProps {
  label: string;
  detail?: string;
  tone?: StatusTone;
  /** Renders on a dark surface (e.g. the hero) instead of a light card. */
  dark?: boolean;
  /** Adds a soft breathing pulse to the dot — reserved for genuinely
   * live/polled state (e.g. a freshly-fetched provider status), never
   * for static standing guarantees, so the motion stays meaningful
   * rather than decorative noise. */
  live?: boolean;
}

const DOT_CLASSES: Record<StatusTone, string> = {
  positive: "bg-emerald-500",
  warning: "bg-amber-500",
  negative: "bg-rose-500",
  neutral: "bg-slate-400",
  info: "bg-brand-500",
};

const LIGHT_SURFACE: Record<StatusTone, string> = {
  positive: "border-emerald-200 bg-emerald-50/60",
  warning: "border-amber-200 bg-amber-50/60",
  negative: "border-rose-200 bg-rose-50/60",
  neutral: "border-slate-200 bg-slate-50",
  info: "border-brand-200 bg-brand-50/60",
};

const LIGHT_TEXT: Record<StatusTone, { label: string; detail: string }> = {
  positive: { label: "text-emerald-900", detail: "text-emerald-800" },
  warning: { label: "text-amber-900", detail: "text-amber-800" },
  negative: { label: "text-rose-900", detail: "text-rose-800" },
  neutral: { label: "text-slate-900", detail: "text-slate-600" },
  info: { label: "text-brand-900", detail: "text-brand-800" },
};

/** A status indicator: dot + label + short detail line. Used for safety
 * guarantees (hero) and live provider status (Settings) — a step up from
 * a plain Badge when a supporting sentence is needed too. */
export function StatusPill({
  label,
  detail,
  tone = "neutral",
  dark = false,
  live = false,
}: StatusPillProps) {
  const dotClasses = `mt-1.5 h-2 w-2 flex-none rounded-full ${DOT_CLASSES[tone]} ${
    live ? "motion-safe:animate-pulse-soft" : ""
  }`;

  if (dark) {
    return (
      <div className="flex flex-1 min-w-[200px] items-start gap-3 rounded-none border border-white/10 bg-white/5 px-4 py-3 backdrop-blur-sm">
        <span className={dotClasses} aria-hidden="true" />
        <div>
          <p className="text-sm font-semibold text-white">{label}</p>
          {detail ? <p className="text-xs text-white/60">{detail}</p> : null}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex flex-1 min-w-[220px] items-start gap-3 rounded-none border px-4 py-3 ${LIGHT_SURFACE[tone]}`}
    >
      <span className={dotClasses} aria-hidden="true" />
      <div>
        <p className={`text-sm font-semibold ${LIGHT_TEXT[tone].label}`}>{label}</p>
        {detail ? <p className={`text-xs ${LIGHT_TEXT[tone].detail}`}>{detail}</p> : null}
      </div>
    </div>
  );
}
