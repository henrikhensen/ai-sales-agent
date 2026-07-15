"use client";

import { useState } from "react";

export interface ServiceItem {
  title: string;
  description: string;
}

interface ServiceListProps {
  items: ServiceItem[];
  className?: string;
}

/** A tiny, original geometric glyph per row (no icon library, no photos) —
 * cycles through four simple stroke arrangements so each of the six rows
 * reads as visually distinct without needing six bespoke assets. */
export function ServiceGlyph({ index }: { index: number }) {
  const shape = index % 4;
  return (
    <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true" focusable="false">
      {shape === 0 ? (
        <rect x="6" y="6" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.5" />
      ) : null}
      {shape === 1 ? (
        <>
          <line x1="6" y1="16" x2="26" y2="16" stroke="currentColor" strokeWidth="1.5" />
          <line x1="16" y1="6" x2="16" y2="26" stroke="currentColor" strokeWidth="1.5" />
        </>
      ) : null}
      {shape === 2 ? (
        <polygon points="16,6 26,26 6,26" fill="none" stroke="currentColor" strokeWidth="1.5" />
      ) : null}
      {shape === 3 ? (
        <rect
          x="9"
          y="9"
          width="14"
          height="14"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          transform="rotate(45 16 16)"
        />
      ) : null}
    </svg>
  );
}

/** The Funktionsbereiche list — six large, sharp-edged rows with a
 * bracketed index, echoing the reference's dark "Services" section
 * rhythm. Each row is a real `<button aria-expanded>` (not a hover-only
 * reveal) that expands to a short description plus a small original
 * glyph, using the same `grid-template-rows` expand technique as the FAQ
 * accordion and `LeadFinderApp`'s candidate details. */
export function ServiceList({ items, className }: ServiceListProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className={`divide-y divide-white/10 border-y border-white/10 ${className ?? ""}`}>
      {items.map((item, index) => {
        const isOpen = openIndex === index;
        const panelId = `service-panel-${index}`;
        const buttonId = `service-button-${index}`;
        return (
          <div key={item.title}>
            <button
              type="button"
              id={buttonId}
              aria-expanded={isOpen}
              aria-controls={panelId}
              onClick={() => setOpenIndex(isOpen ? null : index)}
              onMouseEnter={() => setOpenIndex(index)}
              className="group flex w-full items-baseline gap-4 py-7 text-left outline-none focus-visible:text-white sm:gap-8 sm:py-9"
            >
              <span className="mono-label-invert flex-none">[{String(index + 1).padStart(2, "0")}]</span>
              <span className="flex-1 text-3xl font-black tracking-tight text-white transition-colors duration-150 sm:text-5xl">
                {item.title}
              </span>
            </button>
            <div
              id={panelId}
              role="region"
              aria-labelledby={buttonId}
              className={`grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none ${
                isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
              }`}
            >
              <div className="overflow-hidden">
                <div className="flex items-start gap-5 pb-8 pl-0 pr-6 text-white/70 sm:pl-16">
                  <span className="flex-none text-white/50">
                    <ServiceGlyph index={index} />
                  </span>
                  <p className="max-w-2xl text-sm leading-relaxed sm:text-base">{item.description}</p>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
