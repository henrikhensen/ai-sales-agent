import type { ReactNode } from "react";

type BadgeTone = "neutral" | "positive" | "negative" | "warning" | "info";

interface BadgeProps {
  children: ReactNode;
  tone?: BadgeTone;
}

const toneClasses: Record<BadgeTone, string> = {
  neutral: "bg-slate-100 text-slate-700",
  positive: "bg-emerald-100 text-emerald-700",
  negative: "bg-rose-100 text-rose-700",
  warning: "bg-amber-100 text-amber-800",
  info: "bg-brand-100 text-brand-700",
};

export function Badge({ children, tone = "neutral" }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold tracking-tight ${toneClasses[tone]}`}
    >
      {children}
    </span>
  );
}
