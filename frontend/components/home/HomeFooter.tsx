"use client";

import Link from "next/link";

import { useAuth } from "@/components/auth/AuthProvider";
import { isAdmin } from "@/lib/roles";

interface FooterLink {
  href: string;
  label: string;
}

const TOOLS_LINKS: FooterLink[] = [
  { href: "/sales-strategy/icp", label: "Zielkunde (ICP)" },
  { href: "/sales-strategy/offers", label: "Angebot (Offer)" },
  { href: "/lead-sourcing", label: "Lead Sourcing" },
  { href: "/lead-qualification", label: "Lead Qualifikation" },
  { href: "/workflows/sales", label: "Einzelne Firma manuell analysieren" },
  { href: "/agents", label: "Einzel-Agenten" },
  { href: "/quality", label: "Quality Dashboard" },
  { href: "/onboarding", label: "Setup-Guide" },
];

const COMPLIANCE_LINKS: FooterLink[] = [
  { href: "/compliance/status", label: "Compliance Status" },
  { href: "/compliance/do-not-contact", label: "Do-not-contact" },
];

/** Homepage-only footer — a large wordmark bleed, the existing secondary-
 * tool links (moved here from the old "Weitere Werkzeuge" plain list) plus
 * the compliance routes as this app's stand-in for legal/privacy links
 * (there is no separate legal page in this internal tool, so the footer
 * points at the real compliance routes rather than a dead link), and the
 * standing safety line. Rendered only inside the home page's full-bleed
 * wrapper — every other route keeps `AppShell`'s current layout. */
export function HomeFooter() {
  const { currentUser } = useAuth();

  return (
    <footer className="border-t border-white/10 bg-canvas text-white">
      <div className="container-app py-16 sm:py-20">
        <div className="grid grid-cols-1 gap-12 sm:grid-cols-3">
          <div>
            <p className="mono-label-invert">AI Sales Copilot</p>
            <p className="mt-3 max-w-xs text-sm text-white/60">
              Kontrollierte B2B-Akquise mit echten Firmendaten, klarer Qualifikation und
              menschlicher Prüfung.
            </p>
          </div>

          <div>
            <p className="mono-label-invert">Weitere Werkzeuge</p>
            <ul className="mt-3 space-y-2">
              {TOOLS_LINKS.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="text-sm text-white/60 hover:text-white">
                    {link.label}
                  </Link>
                </li>
              ))}
              {isAdmin(currentUser) ? (
                <li>
                  <Link href="/admin/controls" className="text-sm text-white/60 hover:text-white">
                    Admin Controls
                  </Link>
                </li>
              ) : null}
            </ul>
          </div>

          <div>
            <p className="mono-label-invert">Compliance &amp; Datenschutz</p>
            <ul className="mt-3 space-y-2">
              {COMPLIANCE_LINKS.map((link) => (
                <li key={link.href}>
                  <Link href={link.href} className="text-sm text-white/60 hover:text-white">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div className="mt-12 border-t border-white/10 pt-6">
          <p className="mono-label-invert">Draft-only · kein automatischer Versand</p>
        </div>
      </div>

      <div className="overflow-hidden border-t border-white/10 py-4">
        <p
          className="select-none whitespace-nowrap text-center font-black uppercase leading-none tracking-tight text-white/[0.06]"
          style={{ fontSize: "clamp(3rem, 12vw, 9rem)" }}
          aria-hidden="true"
        >
          AI Sales Copilot
        </p>
      </div>
    </footer>
  );
}
