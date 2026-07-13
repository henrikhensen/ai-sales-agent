import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "dark";
type ButtonSize = "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
}

// Sharp corners, no shadow, hover flips fill/text — the same black/white
// invert signature used by the topic cards, so every clickable primary
// action in the app speaks the same visual language.
const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "border border-ink-950 bg-ink-950 text-white hover:bg-white hover:text-ink-950 disabled:border-ink-300 disabled:bg-ink-300 disabled:text-white",
  secondary:
    "border border-ink-950 bg-transparent text-ink-950 hover:bg-ink-950 hover:text-white disabled:border-ink-300 disabled:text-ink-300",
  ghost: "border border-transparent text-ink-600 hover:text-ink-950 disabled:text-ink-300",
  dark: "border border-white bg-white text-ink-950 hover:bg-transparent hover:text-white disabled:border-white/30 disabled:bg-white/30 disabled:text-white/60",
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
