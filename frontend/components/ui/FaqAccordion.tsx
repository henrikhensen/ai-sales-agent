"use client";

import { useState } from "react";

export interface FaqItem {
  question: string;
  answer: string;
}

interface FaqAccordionProps {
  items: FaqItem[];
  className?: string;
}

/** Accessible single-open accordion — sharp hairline-bordered rows, a
 * `+`/`×` indicator, and the same `grid-template-rows: 0fr → 1fr` expand
 * technique already used for candidate details in `LeadFinderApp.tsx`, so
 * the whole app shares one expand/collapse motion language instead of two.
 * Each row is a real `<button aria-expanded>` — full keyboard operation,
 * not a hover-only reveal. */
export function FaqAccordion({ items, className }: FaqAccordionProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className={`divide-y divide-muted/15 border-y border-muted/15 ${className ?? ""}`}>
      {items.map((item, index) => {
        const isOpen = openIndex === index;
        const panelId = `faq-panel-${index}`;
        const buttonId = `faq-button-${index}`;
        return (
          <div key={item.question}>
            <h3>
              <button
                type="button"
                id={buttonId}
                aria-expanded={isOpen}
                aria-controls={panelId}
                onClick={() => setOpenIndex(isOpen ? null : index)}
                className="flex w-full items-center justify-between gap-6 py-6 text-left outline-none focus-visible:text-muted"
              >
                <span className="text-lg font-bold tracking-tight text-muted sm:text-xl">
                  {item.question}
                </span>
                <span
                  className="flex-none text-2xl font-light leading-none text-muted/50 transition-transform duration-200 motion-reduce:transition-none"
                  style={{ transform: isOpen ? "rotate(45deg)" : "rotate(0deg)" }}
                  aria-hidden="true"
                >
                  +
                </span>
              </button>
            </h3>
            <div
              id={panelId}
              role="region"
              aria-labelledby={buttonId}
              className={`grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none ${
                isOpen ? "grid-rows-[1fr]" : "grid-rows-[0fr]"
              }`}
            >
              <div className="overflow-hidden">
                <p className="pb-6 pr-10 text-sm leading-relaxed text-muted/65">{item.answer}</p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
