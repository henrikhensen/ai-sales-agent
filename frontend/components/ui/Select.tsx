import type { SelectHTMLAttributes } from "react";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: SelectOption[];
  hint?: string;
}

export function Select({ label, options, hint, id, className, ...rest }: SelectProps) {
  const selectId = id ?? `select-${label.toLowerCase().replace(/\s+/g, "-")}`;
  return (
    <div>
      <label className="field-label" htmlFor={selectId}>
        {label}
      </label>
      <select
        id={selectId}
        className={`w-full rounded-lg border border-muted/25 bg-canvas px-3 py-2 text-sm text-muted outline-none transition-colors duration-150 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30 ${className ?? ""}`}
        {...rest}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint ? <p className="field-hint">{hint}</p> : null}
    </div>
  );
}
