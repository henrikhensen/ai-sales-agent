import type { ReactNode } from "react";

type CardVariant = "default" | "framed" | "dark" | "flat";

interface CardProps {
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
  /** default: the standard work-surface card (`surface` bordeaux, subtle
   *  muted-tinted hairline border) used everywhere. framed: a full-
   *  opacity `muted` border + more padding, for the one or two panels
   *  per page that should read as the primary surface (e.g. the Lead
   *  Finder input panel). dark: a deeper, near-black `canvas` block with
   *  a white-tinted border — for a compact, higher-contrast statement
   *  (e.g. the Safety block), never the default. flat: a barely-there
   *  translucent white tint over canvas, no border weight — for
   *  de-emphasized secondary content. */
  variant?: CardVariant;
  /** Subtle hover lift (no shadow, stays flat/kantig) for cards that are
   * themselves a result of an action — e.g. a candidate or past-run card
   * — signalling "this row responds to you" without any color change. */
  interactive?: boolean;
}

const INTERACTIVE_CLASSES =
  "transition-transform duration-150 hover:-translate-y-0.5 motion-reduce:hover:translate-y-0";

// Complete class strings per variant (not merged utility fragments) so a
// variant can never partially cancel another Tailwind class of equal
// specificity depending on generation order.
const VARIANT_CLASSES: Record<CardVariant, string> = {
  default: "rounded-none border border-muted/15 bg-surface p-6 sm:p-7",
  framed: "rounded-none border-2 border-muted bg-surface p-8 sm:p-12",
  dark: "rounded-none border border-white/15 bg-canvas p-6 sm:p-7",
  flat: "rounded-none border border-muted/10 bg-white/[0.03] p-6 sm:p-7",
};

const TITLE_CLASSES: Record<CardVariant, string> = {
  default: "text-base font-semibold tracking-tight text-muted",
  framed: "text-xl font-bold tracking-tight text-muted",
  dark: "text-base font-semibold tracking-tight text-white",
  flat: "text-base font-semibold tracking-tight text-muted",
};

const DESCRIPTION_CLASSES: Record<CardVariant, string> = {
  default: "mt-1 text-sm text-muted/55",
  framed: "mt-2 text-sm text-muted/55",
  dark: "mt-1 text-sm text-white/60",
  flat: "mt-1 text-sm text-muted/55",
};

export function Card({
  title,
  description,
  children,
  className,
  variant = "default",
  interactive = false,
}: CardProps) {
  return (
    <div
      className={`${VARIANT_CLASSES[variant]} ${interactive ? INTERACTIVE_CLASSES : ""} ${className ?? ""}`}
    >
      {title ? <h2 className={TITLE_CLASSES[variant]}>{title}</h2> : null}
      {description ? <p className={DESCRIPTION_CLASSES[variant]}>{description}</p> : null}
      <div className={title || description ? "mt-4" : ""}>{children}</div>
    </div>
  );
}
