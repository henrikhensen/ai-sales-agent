type StatusTone = "positive" | "warning" | "negative" | "neutral" | "info";

interface StatusPillProps {
  label: string;
  detail?: string;
  tone?: StatusTone;
  /** Slightly stronger border/fill — for use directly on `canvas`
   * (darkest background) rather than a `surface` card, where the
   * default treatment already has enough contrast. */
  dark?: boolean;
  /** Adds a soft breathing pulse to the dot — reserved for genuinely
   * live/polled state (e.g. a freshly-fetched provider status), never
   * for static standing guarantees, so the motion stays meaningful
   * rather than decorative noise. */
  live?: boolean;
}

const DOT_CLASSES: Record<StatusTone, string> = {
  positive: "bg-emerald-400",
  warning: "bg-amber-400",
  negative: "bg-rose-400",
  neutral: "bg-muted/50",
  info: "bg-brand-500",
};

// Translucent tints on the dark surface — legible without ever painting
// a solid green/blue/yellow block. `dark` bumps the border/fill opacity
// slightly since `canvas` is a touch darker than `surface`.
const SURFACE_CLASSES: Record<StatusTone, string> = {
  positive: "border-emerald-400/25 bg-emerald-400/10",
  warning: "border-amber-400/25 bg-amber-400/10",
  negative: "border-rose-400/25 bg-rose-400/10",
  neutral: "border-muted/15 bg-white/5",
  info: "border-brand-500/30 bg-brand-500/10",
};

const TEXT_CLASSES: Record<StatusTone, { label: string; detail: string }> = {
  positive: { label: "text-emerald-200", detail: "text-emerald-200/70" },
  warning: { label: "text-amber-200", detail: "text-amber-200/70" },
  negative: { label: "text-rose-200", detail: "text-rose-200/70" },
  neutral: { label: "text-muted", detail: "text-muted/60" },
  info: { label: "text-muted", detail: "text-muted/60" },
};

/** A status indicator: dot + label + short detail line. Used for safety
 * guarantees and live provider status — a step up from a plain Badge
 * when a supporting sentence is needed too. */
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

  return (
    <div
      className={`flex flex-1 min-w-[220px] items-start gap-3 rounded-none border px-4 py-3 ${SURFACE_CLASSES[tone]} ${dark ? "backdrop-blur-sm" : ""}`}
    >
      <span className={dotClasses} aria-hidden="true" />
      <div>
        <p className={`text-sm font-semibold ${TEXT_CLASSES[tone].label}`}>{label}</p>
        {detail ? <p className={`text-xs ${TEXT_CLASSES[tone].detail}`}>{detail}</p> : null}
      </div>
    </div>
  );
}
