interface SkeletonProps {
  className?: string;
}

/** A single loading placeholder bar/block — built on Tailwind's own
 * `animate-pulse` (no custom keyframe needed). Compose a few of these
 * inside a `Card` to preview a card's real layout while data loads,
 * instead of leaving an empty area or a plain "wird geladen…" line. */
export function Skeleton({ className }: SkeletonProps) {
  return <div className={`animate-pulse rounded-none bg-ink-100 ${className ?? ""}`} aria-hidden="true" />;
}

/** A Card-shaped skeleton matching the past-run card's real proportions,
 * so the layout doesn't shift once real data replaces it. */
export function SkeletonRunCard() {
  return (
    <div className="rounded-none border border-ink-950/10 bg-white p-6 sm:p-7">
      <div className="flex items-start justify-between gap-2">
        <Skeleton className="h-4 w-2/5" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="mt-3 h-3 w-1/3" />
      <div className="mt-4 grid grid-cols-2 gap-2">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
      <div className="mt-4 flex items-center justify-between">
        <Skeleton className="h-3 w-1/3" />
        <Skeleton className="h-3 w-12" />
      </div>
    </div>
  );
}
