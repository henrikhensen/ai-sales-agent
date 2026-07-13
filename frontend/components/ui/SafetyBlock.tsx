interface SafetyItem {
  label: string;
  detail: string;
}

interface SafetyBlockProps {
  items: SafetyItem[];
}

/** Compact, solid dark block stating the standing safety guarantees —
 * deliberately flat (no colored pills/icons) so it reads as a firm
 * statement of fact rather than a wall of warning color. Used once per
 * page, never scattered as decoration. */
export function SafetyBlock({ items }: SafetyBlockProps) {
  return (
    <div className="border border-ink-950 bg-ink-950 text-white">
      <div className="border-b border-white/15 px-6 py-4 sm:px-10">
        <span className="mono-label-invert">Safety</span>
      </div>
      <dl className="divide-y divide-white/10 sm:grid sm:grid-cols-3 sm:divide-x sm:divide-y-0">
        {items.map((item) => (
          <div key={item.label} className="px-6 py-6 sm:px-8">
            <dt className="text-base font-bold tracking-tight">{item.label}</dt>
            <dd className="mt-1.5 text-sm text-white/60">{item.detail}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
