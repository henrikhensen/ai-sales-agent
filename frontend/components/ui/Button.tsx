import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "dark";
type ButtonSize = "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

// Sharp corners, no shadow, hover flips fill/text — the same invert
// signature used by the topic cards, so every clickable primary action
// speaks the same visual language. `muted` (the palette's soft-contrast
// tone) carries the fill for everyday primary actions; literal white is
// reserved for the rare `dark` variant — the one or two truly critical
// CTAs per page, per the brand brief's "white only for small accents or
// strong CTAs" rule.
const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "border border-muted bg-muted text-canvas hover:bg-transparent hover:text-muted disabled:border-muted/25 disabled:bg-muted/25 disabled:text-canvas/50",
  secondary:
    "border border-muted/50 bg-transparent text-muted hover:bg-muted hover:text-canvas disabled:border-muted/20 disabled:text-muted/30",
  ghost: "border border-transparent text-muted/70 hover:text-muted disabled:text-muted/30",
  dark: "border border-white bg-white text-canvas hover:bg-transparent hover:text-white disabled:border-white/25 disabled:bg-white/25 disabled:text-white/50",
};

const sizeClasses: Record<ButtonSize, string> = {
  md: "px-4 py-2 text-xs",
  lg: "px-7 py-3.5 text-sm",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  children,
  className,
  ...rest
}: ButtonProps) {
  // The loud uppercase/tracked treatment is reserved for large CTAs (the
  // hero/section-level actions) — every smaller button across the app's
  // utility pages (Settings, CRM, Reviews, ...) keeps a calmer sentence
  // case so those pages stay secondary, not shouting.
  const caps = size === "lg" && variant !== "ghost";
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 rounded-none font-bold transition duration-150 active:scale-[0.97] motion-reduce:active:scale-100 disabled:cursor-not-allowed disabled:active:scale-100 ${caps ? "uppercase tracking-wide" : ""} ${sizeClasses[size]} ${variantClasses[variant]} ${className ?? ""}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? (
        <span
          className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          aria-hidden="true"
        />
      ) : null}
      {children}
    </button>
  );
}
