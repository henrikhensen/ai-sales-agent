"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { useAuth } from "@/components/auth/AuthProvider";
import {
  canManageDataRetention,
  canManageReviews,
  canRunSalesWorkflow,
  canViewAdminControls,
  canViewAuditLogs,
  canViewBetaTestSessions,
  canViewComplianceDocuments,
  canViewCRM,
  canViewComplianceStatus,
  canViewQuality,
  canViewRealWorldTestRuns,
  canViewReplies,
  canViewResearch,
  canViewSalesStrategy,
  canViewSystemStatus,
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
  // Beginner-facing sections render as a plain list. "Erweitert" (advanced/
  // admin-only tooling) renders as a collapsed <details> disclosure instead
  // — reachable, but not competing for attention on first use.
  collapsible?: boolean;
}

const ALWAYS_VISIBLE = () => true;

const NAV_SECTIONS: NavSection[] = [
  {
    title: "Start",
    items: [
      { href: "/", label: "Command Center", visible: ALWAYS_VISIBLE },
      { href: "/onboarding", label: "Setup-Guide", visible: ALWAYS_VISIBLE },
    ],
  },
  {
    title: "Verkaufen",
    items: [
      { href: "/sales-strategy/icp", label: "Zielkunde (ICP)", visible: canViewSalesStrategy },
      { href: "/sales-strategy/offers", label: "Angebot (Offer)", visible: canViewSalesStrategy },
      { href: "/lead-sourcing", label: "Lead Sourcing", visible: ALWAYS_VISIBLE },
      { href: "/lead-qualification", label: "Lead Qualifikation", visible: ALWAYS_VISIBLE },
      { href: "/workflows/sales", label: "Sales Workflow", visible: canRunSalesWorkflow },
      { href: "/crm", label: "Drafts (CRM)", visible: canViewCRM },
      { href: "/crm/pipeline", label: "CRM Pipeline", visible: canViewCRM },
      { href: "/reviews", label: "Human Review", visible: canManageReviews },
      { href: "/outreach", label: "Outreach Queue", visible: ALWAYS_VISIBLE },
    ],
  },
  {
    title: "Postfach",
    items: [{ href: "/replies", label: "Replies", visible: canViewReplies }],
  },
  {
    title: "Sicherheit",
    items: [
      { href: "/compliance/status", label: "Compliance Status", visible: canViewComplianceStatus },
      { href: "/compliance/do-not-contact", label: "Do-not-contact", visible: ALWAYS_VISIBLE },
    ],
  },
  {
    title: "Erweitert",
    collapsible: true,
    items: [
      { href: "/workflows", label: "Workflows (Übersicht)", visible: (user) => hasRole(user, ["admin"]) },
      { href: "/workflows/history", label: "Workflow History", visible: canViewWorkflowHistory },
      { href: "/outreach/dispatch", label: "Outreach Dispatch", visible: ALWAYS_VISIBLE },
      { href: "/research/website", label: "Website Research (einzeln)", visible: canViewResearch },
      { href: "/agents", label: "Alle Agenten", visible: ALWAYS_VISIBLE },
      { href: "/agents/lead-research", label: "Agent: Lead Research", visible: ALWAYS_VISIBLE },
      {
        href: "/agents/company-intelligence",
        label: "Agent: Company Intelligence",
        visible: ALWAYS_VISIBLE,
      },
      { href: "/agents/personalization", label: "Agent: Personalization", visible: ALWAYS_VISIBLE },
      { href: "/agents/email-draft", label: "Agent: Email Draft", visible: ALWAYS_VISIBLE },
      { href: "/agents/reply-analysis", label: "Agent: Reply Analysis", visible: ALWAYS_VISIBLE },
      { href: "/quality", label: "Quality Dashboard", visible: canViewQuality },
      { href: "/quality/feedback", label: "Feedback", visible: ALWAYS_VISIBLE },
      { href: "/beta-test", label: "Beta Test", visible: canViewBetaTestSessions },
      { href: "/real-world-test", label: "Real-World Test Mode", visible: canViewRealWorldTestRuns },
      {
        href: "/compliance/documents",
        label: "Compliance Documents",
        visible: canViewComplianceDocuments,
      },
      {
        href: "/compliance/data-retention",
        label: "Data Retention",
        visible: canManageDataRetention,
      },
      {
        href: "/compliance/data-requests",
        label: "Data Requests",
        visible: canManageDataRetention,
      },
      { href: "/audit-logs", label: "Audit Logs", visible: canViewAuditLogs },
      { href: "/system/status", label: "System Status", visible: canViewSystemStatus },
      { href: "/users", label: "Users/Admin", visible: canViewUsers },
      { href: "/admin/controls", label: "Admin Controls", visible: canViewAdminControls },
      { href: "/settings", label: "Einstellungen", visible: ALWAYS_VISIBLE },
    ],
  },
];

interface SidebarProps {
  onNavigate?: () => void;
}

function isItemActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const pathname = usePathname();
  const { currentUser } = useAuth();

  return (
    <nav className="flex h-full w-64 flex-col gap-6 overflow-y-auto border-r border-slate-200 bg-white px-4 py-6">
      <div className="px-2">
        <p className="text-lg font-semibold text-slate-900">AI Sales Copilot</p>
        <p className="text-xs text-slate-500">Analyse, Qualifikation &amp; Entwürfe</p>
      </div>
      {NAV_SECTIONS.map((section) => {
        const visibleItems = section.items.filter((item) => item.visible(currentUser));
        if (visibleItems.length === 0) {
          return null;
        }

        const sectionHasActiveItem = visibleItems.some((item) =>
          isItemActive(pathname, item.href)
        );

        const list = (
          <ul className="mt-2 space-y-1">
            {visibleItems.map((item) => {
              const isActive = isItemActive(pathname, item.href);
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
        );

        if (section.collapsible) {
          return (
            <details key={section.title} className="group" open={sectionHasActiveItem}>
              <summary className="cursor-pointer list-none px-2 text-xs font-semibold uppercase tracking-wide text-slate-400 hover:text-slate-600">
                {section.title}
                <span className="float-right transition-transform group-open:rotate-90">›</span>
              </summary>
              {list}
            </details>
          );
        }

        return (
          <div key={section.title}>
            <p className="px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              {section.title}
            </p>
            {list}
          </div>
        );
      })}
    </nav>
  );
}
