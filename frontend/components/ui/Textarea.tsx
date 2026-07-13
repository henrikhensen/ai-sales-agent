import type { TextareaHTMLAttributes } from "react";

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string;
  hint?: string;
}

export function Textarea({ label, hint, id, className, ...rest }: TextareaProps) {
  const textareaId = id ?? `textarea-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div>
      <label className="field-label" htmlFor={textareaId}>
        {label}
      </label>
      <textarea
        id={textareaId}
        rows={4}
        className={`w-full rounded-lg border border-muted/25 bg-canvas px-3 py-2 text-sm text-muted outline-none transition-colors duration-150 placeholder:text-muted/35 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 ${className ?? ""}`}
        {...rest}
      />
      {hint ? <p className="field-hint">{hint}</p> : null}
    </div>
  );
}
