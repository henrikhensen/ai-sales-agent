"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  canManageReviews,
  canRunSalesWorkflow,
  canViewCRM,
  canViewUsers,
  canViewWorkflowHistory,
  hasRole,
} from "@/lib/roles";
import type { User } from "@/lib/types";

interface NavItem {
  href: string;
  label: string;
  visible: (user: User | null) => boolean;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const ALWAYS_VISIBLE = () => true;

const NAV_SECTIONS: NavSection[] = [
  {
    title: "Übersicht",
    items: [
      { href: "/", label: "Dashboard", visible: ALWAYS_VISIBLE },
      { href: "/crm", label: "CRM", visible: canViewCRM },
      { href: "/reviews", label: "Human Review", visible: canManageReviews },
      { href: "/settings", label: "Einstellungen", visible: ALWAYS_VISIBLE },
    ],
  },
  {
    title: "Agenten",
    items: [
      { href: "/agents", label: "Alle Agenten", visible: ALWAYS_VISIBLE },
      { href: "/agents/lead-research", label: "Lead Research", visible: ALWAYS_VISIBLE },
      {
        href: "/agents/company-intelligence",
        label: "Company Intelligence",
        visible: ALWAYS_VISIBLE,
      },
      { href: "/agents/personalization", label: "Personalization", visible: ALWAYS_VISIBLE },
      { href: "/agents/email-draft", label: "Email Draft", visible: ALWAYS_VISIBLE },
      { href: "/agents/reply-analysis", label: "Reply Analysis", visible: ALWAYS_VISIBLE },
    ],
  },
  {
    title: "Workflows",
    items: [
      { href: "/workflows", label: "Workflows", visible: (user) => hasRole(user, ["admin"]) },
      { href: "/workflows/sales", label: "Sales Workflow", visible: canRunSalesWorkflow },
      { href: "/workflows/history", label: "Workflow History", visible: canViewWorkflowHistory },
    ],
  },
  {
    title: "Verwaltung",
    items: [{ href: "/users", label: "Users/Admin", visible: canViewUsers }],
  },
];

interface SidebarProps {
  onNavigate?: () => void;
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const pathname = usePathname();
  const { currentUser } = useAuth();

  return (
    <nav className="flex h-full w-64 flex-col gap-6 overflow-y-auto border-r border-slate-200 bg-white px-4 py-6">
      <div className="px-2">
        <p className="text-lg font-semibold text-slate-900">AI Sales Agent</p>
        <p className="text-xs text-slate-500">Analyse- &amp; Entwurfswerkzeuge</p>
      </div>
      {NAV_SECTIONS.map((section) => {
        const visibleItems = section.items.filter((item) => item.visible(currentUser));
        if (visibleItems.length === 0) {
          return null;
        }
        return (
          <div key={section.title}>
            <p className="px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              {section.title}
            </p>
            <ul className="mt-2 space-y-1">
              {visibleItems.map((item) => {
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
        );
      })}
    </nav>
  );
}
