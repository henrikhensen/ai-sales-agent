import type { ReactNode } from "react";

type CardVariant = "default" | "framed" | "dark" | "flat";

interface CardProps {
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
  /** default: thin hairline border, white — the standard work-surface
   *  card used everywhere. framed: thicker border + more padding, for the
   *  one or two panels per page that should read as the primary surface
   *  (e.g. the Lead Finder input panel). dark: solid ink background for
   *  a compact contrast block. flat: no border/shadow, bone background —
   *  for de-emphasized secondary content. */
  variant?: CardVariant;
}

// Complete class strings per variant (not merged utility fragments) so a
// variant can never partially cancel another Tailwind class of equal
// specificity depending on generation order.
const VARIANT_CLASSES: Record<CardVariant, string> = {
  default: "rounded-none border border-ink-950/10 bg-white p-6 sm:p-7",
  framed: "rounded-none border-2 border-ink-950 bg-white p-8 sm:p-12",
  dark: "rounded-none border border-white/10 bg-ink-950 p-6 text-white sm:p-7",
  flat: "rounded-none border-0 bg-bone p-6 sm:p-7",
};

const TITLE_CLASSES: Record<CardVariant, string> = {
  default: "text-base font-semibold tracking-tight text-ink-950",
  framed: "text-xl font-bold tracking-tight text-ink-950",
  dark: "text-base font-semibold tracking-tight text-white",
  flat: "text-base font-semibold tracking-tight text-ink-950",
};

const DESCRIPTION_CLASSES: Record<CardVariant, string> = {
  default: "mt-1 text-sm text-ink-500",
  framed: "mt-2 text-sm text-ink-500",
  dark: "mt-1 text-sm text-white/60",
  flat: "mt-1 text-sm text-ink-500",
};

export function Card({ title, description, children, className, variant = "default" }: CardProps) {
  return (
    <div className={`${VARIANT_CLASSES[variant]} ${className ?? ""}`}>
      {title ? <h2 className={TITLE_CLASSES[variant]}>{title}</h2> : null}
      {description ? <p className={DESCRIPTION_CLASSES[variant]}>{description}</p> : null}
      <div className={title || description ? "mt-4" : ""}>{children}</div>
    </div>
  );
}
