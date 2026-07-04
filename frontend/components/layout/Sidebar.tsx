"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface NavItem {
  href: string;
  label: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: "Übersicht",
    items: [
      { href: "/", label: "Dashboard" },
      { href: "/crm", label: "CRM" },
      { href: "/settings", label: "Einstellungen" },
    ],
  },
  {
    title: "Agenten",
    items: [
      { href: "/agents", label: "Alle Agenten" },
      { href: "/agents/lead-research", label: "Lead Research" },
      { href: "/agents/company-intelligence", label: "Company Intelligence" },
      { href: "/agents/personalization", label: "Personalization" },
      { href: "/agents/email-draft", label: "Email Draft" },
      { href: "/agents/reply-analysis", label: "Reply Analysis" },
    ],
  },
];

interface SidebarProps {
  onNavigate?: () => void;
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const pathname = usePathname();

  return (
    <nav className="flex h-full w-64 flex-col gap-6 overflow-y-auto border-r border-slate-200 bg-white px-4 py-6">
      <div className="px-2">
        <p className="text-lg font-semibold text-slate-900">AI Sales Agent</p>
        <p className="text-xs text-slate-500">Analyse- &amp; Entwurfswerkzeuge</p>
      </div>
      {NAV_SECTIONS.map((section) => (
        <div key={section.title}>
          <p className="px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            {section.title}
          </p>
          <ul className="mt-2 space-y-1">
            {section.items.map((item) => {
              const isActive =
                item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    onClick={onNavigate}
                    className={`block rounded-lg px-2 py-1.5 text-sm font-medium transition-colors ${
                      isActive
                        ? "bg-brand-50 text-brand-700"
                        : "text-slate-600 hover:bg-slate-100"
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}
