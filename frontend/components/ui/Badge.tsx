import type { ReactNode } from "react";

type BadgeTone = "neutral" | "positive" | "negative" | "warning" | "info";

interface BadgeProps {
  children: ReactNode;
  tone?: BadgeTone;
}

// Translucent, desaturated tints over the dark surface — status stays
// legible without ever reading as a bold green/blue/yellow "badge wall".
// Semantic color is kept only where it's functionally necessary
// (qualified vs. rejected vs. needs-review), always this quiet.
const toneClasses: Record<BadgeTone, string> = {
  neutral: "bg-white/10 text-muted/80",
  positive: "bg-emerald-500/15 text-emerald-300",
  negative: "bg-rose-500/15 text-rose-300",
  warning: "bg-amber-500/15 text-amber-300",
  info: "bg-brand-500/20 text-brand-800",
};

export function Badge({ children, tone = "neutral" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-none px-2.5 py-1 text-xs font-semibold tracking-tight ${toneClasses[tone]}`}
    >
      {children}
    </span>
  );
}
