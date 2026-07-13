import type { ReactNode } from "react";

interface SectionHeaderProps {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

/** Standard section heading used across pages: small uppercase eyebrow,
 * a bold section title, an optional supporting sentence, and an optional
 * right-aligned action (link/button) — keeps section intros consistent
 * instead of every page hand-rolling its own heading markup. */
export function SectionHeader({
  eyebrow,
  title,
  description,
  action,
  className,
}: SectionHeaderProps) {
  return (
    <div className={`flex flex-wrap items-end justify-between gap-4 ${className ?? ""}`}>
      <div className="max-w-2xl">
        {eyebrow ? <span className="section-eyebrow">{eyebrow}</span> : null}
        <h2 className="section-title">{title}</h2>
        {description ? <p className="mt-2 text-sm text-slate-600">{description}</p> : null}
      </div>
      {action ? <div className="flex-none">{action}</div> : null}
    </div>
  );
}
