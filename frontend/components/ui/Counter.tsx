"use client";

import { useEffect, useRef, useState } from "react";

interface CounterProps {
  /** The final integer value — always a real product principle or fact
   * (e.g. "0 automatische Send-Aktionen"), never an invented customer
   * statistic. */
  value: number;
  prefix?: string;
  suffix?: string;
  label: string;
  description?: string;
  className?: string;
}

const COUNT_DURATION_MS = 900;

/** A big count-up figure that animates from 0 to its final value the first
 * time it scrolls into view — same `IntersectionObserver` pattern as
 * `Reveal`, self-disconnecting, degrades to showing the final value
 * immediately if `IntersectionObserver` is unsupported or the user has
 * asked for reduced motion (checked once at mount, not re-derived per
 * frame). Never re-triggers on scroll-back. */
export function Counter({ value, prefix = "", suffix = "", label, description, className }: CounterProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [display, setDisplay] = useState(0);
  const startedRef = useRef(false);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;

    const prefersReducedMotion =
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (typeof IntersectionObserver === "undefined" || prefersReducedMotion) {
      setDisplay(value);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !startedRef.current) {
          startedRef.current = true;
          const start = performance.now();
          function tick(now: number) {
            const progress = Math.min(1, (now - start) / COUNT_DURATION_MS);
            setDisplay(Math.round(value * progress));
            if (progress < 1) {
              requestAnimationFrame(tick);
            }
          }
          requestAnimationFrame(tick);
          observer.disconnect();
        }
      },
      { threshold: 0.4 }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [value]);

  return (
    <div ref={ref} className={className}>
      <p className="text-4xl font-black tracking-tight text-muted sm:text-5xl">
        {prefix}
        {display}
        {suffix}
      </p>
      <div className="mt-3 border-t border-dashed border-muted/25" aria-hidden="true" />
      <p className="mt-3 text-sm font-bold text-muted">{label}</p>
      {description ? <p className="mt-1 text-sm text-muted/55">{description}</p> : null}
    </div>
  );
}
