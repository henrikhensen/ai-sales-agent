"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

interface RevealProps {
  children: ReactNode;
  /** Stagger delay in ms, applied only once the element is in view. */
  delayMs?: number;
  className?: string;
}

/** Fades an element up into place the first time it scrolls into the
 * viewport — the scroll-triggered counterpart to the plain mount-time
 * `animate-fade-in-up` used above the fold. Built on the browser's native
 * `IntersectionObserver` (no animation library): each section/card reveals
 * once, self-disconnects, and never re-triggers on scroll-back. Content is
 * always in the DOM (never `display:none`), so it's never hidden from
 * assistive tech or search — only its opacity/position animates in. */
export function Reveal({ children, delayMs = 0, className }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    // No IntersectionObserver support (very old browsers): show content
    // immediately rather than risk it staying invisible forever.
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -10% 0px" }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`${visible ? "animate-fade-in-up" : "opacity-0"} ${className ?? ""}`}
      style={visible ? { animationDelay: `${delayMs}ms` } : undefined}
    >
      {children}
    </div>
  );
}
