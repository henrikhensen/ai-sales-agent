"use client";

import type { ReactNode } from "react";

/** Next.js remounts `template.tsx` (unlike `layout.tsx`) on every
 * navigation, which is exactly the hook needed for a page transition
 * without a client-side router/animation library: each new page fades
 * and slides up into place while the persistent Header/Sidebar chrome
 * never re-renders. Entrance-only (no exit animation) keeps it fast and
 * avoids the complexity of orchestrating an unmount — deliberately
 * subtle, not a "spielerei" effect. */
export default function Template({ children }: { children: ReactNode }) {
  return <div className="animate-fade-in-up">{children}</div>;
}
