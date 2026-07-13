import type { ReactNode } from "react";

interface SectionHeaderProps {
  /** Optional index, e.g. "01" — this app's sections are a genuine
   * numbered sequence (hero → workflow → lead finder → results →
   * safety), so a number here is informative, not decorative. */
  index?: string;
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

/** Standard editorial section heading: optional index + mono eyebrow over
 * a large bold title, a hairline rule underneath, an optional supporting
 * sentence, and an optional right-aligned action. */
export function SectionHeader({
  index,
  eyebrow,
  title,
  description,
  action,
  className,
}: SectionHeaderProps) {
  return (
    <div className={`border-b border-muted/15 pb-6 ${className ?? ""}`}>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="max-w-2xl">
          {eyebrow ? (
            <span className="mono-label">
              {index ? `${index} — ` : ""}
              {eyebrow}
            </span>
          ) : null}
          <h2 className="mt-2 text-3xl font-bold tracking-tight text-muted sm:text-4xl">
            {title}
          </h2>
          {description ? <p className="mt-3 text-base text-muted/60">{description}</p> : null}
        </div>
        {action ? <div className="flex-none">{action}</div> : null}
      </div>
    </div>
  );
}
