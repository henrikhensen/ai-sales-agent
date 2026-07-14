import type { InputHTMLAttributes } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
}

export function Input({ label, hint, id, className, ...rest }: InputProps) {
  const inputId = id ?? `input-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div>
      <label className="field-label" htmlFor={inputId}>
        {label}
      </label>
      <input
        id={inputId}
        className={`w-full rounded-none border border-muted/25 bg-canvas px-3 py-2 text-sm text-muted outline-none transition-colors duration-150 placeholder:text-muted/35 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 ${className ?? ""}`}
        {...rest}
      />
      {hint ? <p className="field-hint">{hint}</p> : null}
    </div>
  );
}
