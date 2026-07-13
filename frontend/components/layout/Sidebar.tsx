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
  canViewLeadDiscovery,
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

const ALWAYS_VISIBLE = () => true;

// The visible main navigation is deliberately short — five destinations a
// beginner can hold in their head. Everything else (admin, audit,
// compliance detail, provider settings, individual agents, …) stays
// reachable under "Erweitert", collapsed by default.
const MAIN_ITEMS: NavItem[] = [
  { href: "/", label: "Start", visible: ALWAYS_VISIBLE },
  { href: "/lead-finder", label: "Lead Finder", visible: canViewLeadDiscovery },
  { href: "/reviews", label: "Reviews", visible: canManageReviews },
  { href: "/crm/pipeline", label: "Leads", visible: canViewCRM },
  { href: "/settings", label: "Einstellungen", visible: ALWAYS_VISIBLE },
];

const ADVANCED_ITEMS: NavItem[] = [
  { href: "/onboarding", label: "Setup-Guide", visible: ALWAYS_VISIBLE },
  { href: "/sales-strategy/icp", label: "Zielkunde (ICP)", visible: canViewSalesStrategy },
  { href: "/sales-strategy/offers", label: "Angebot (Offer)", visible: canViewSalesStrategy },
  { href: "/lead-sourcing", label: "Lead Sourcing", visible: ALWAYS_VISIBLE },
  { href: "/lead-qualification", label: "Lead Qualifikation", visible: ALWAYS_VISIBLE },
  { href: "/workflows/sales", label: "Sales Workflow (einzeln)", visible: canRunSalesWorkflow },
  { href: "/crm", label: "Drafts (CRM)", visible: canViewCRM },
  { href: "/outreach", label: "Outreach Queue", visible: ALWAYS_VISIBLE },
  { href: "/outreach/dispatch", label: "Outreach Dispatch", visible: ALWAYS_VISIBLE },
  { href: "/replies", label: "Replies", visible: canViewReplies },
  { href: "/compliance/status", label: "Compliance Status", visible: canViewComplianceStatus },
  { href: "/compliance/do-not-contact", label: "Do-not-contact", visible: ALWAYS_VISIBLE },
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
  { href: "/workflows", label: "Workflows (Übersicht)", visible: (user) => hasRole(user, ["admin"]) },
  { href: "/workflows/history", label: "Workflow History", visible: canViewWorkflowHistory },
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
  { href: "/audit-logs", label: "Audit Logs", visible: canViewAuditLogs },
  { href: "/system/status", label: "System Status", visible: canViewSystemStatus },
  { href: "/users", label: "Users/Admin", visible: canViewUsers },
  { href: "/admin/controls", label: "Admin Controls", visible: canViewAdminControls },
];

interface SidebarProps {
  onNavigate?: () => void;
}

function isItemActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function NavList({
  items,
  pathname,
  onNavigate,
}: {
  items: NavItem[];
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <ul className="mt-2 space-y-0.5">
      {items.map((item) => {
        const isActive = isItemActive(pathname, item.href);
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              onClick={onNavigate}
              className={`block border-l-2 py-1.5 pl-3 text-sm transition-colors ${
                isActive
                  ? "border-l-ink-950 font-semibold text-ink-950"
                  : "border-l-transparent text-ink-500 hover:border-l-ink-300 hover:text-ink-950"
              }`}
            >
              {item.label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const pathname = usePathname();
  const { currentUser } = useAuth();

  const visibleMainItems = MAIN_ITEMS.filter((item) => item.visible(currentUser));
  const visibleAdvancedItems = ADVANCED_ITEMS.filter((item) => item.visible(currentUser));
  const advancedHasActiveItem = visibleAdvancedItems.some((item) =>
    isItemActive(pathname, item.href)
  );

  return (
    <nav className="flex h-full w-56 flex-col gap-8 overflow-y-auto border-r border-ink-950/10 bg-white px-4 py-6">
      <div className="border-b border-ink-950/10 px-3 pb-4">
        <p className="mono-label">AI Sales Copilot</p>
      </div>

      <NavList items={visibleMainItems} pathname={pathname} onNavigate={onNavigate} />

      {visibleAdvancedItems.length > 0 ? (
        <details className="group" open={advancedHasActiveItem}>
          <summary className="cursor-pointer list-none pl-3 text-xs font-semibold uppercase tracking-wide text-ink-400 hover:text-ink-950">
            Erweitert
            <span className="float-right transition-transform group-open:rotate-90">›</span>
          </summary>
          <NavList items={visibleAdvancedItems} pathname={pathname} onNavigate={onNavigate} />
        </details>
      ) : null}
    </nav>
  );
}
