import type { User, UserRole } from "./types";

// Role-based access control helpers for the frontend. These mirror the
// backend's role matrix (see backend/api/dependencies/auth.py) but only
// ever decide what to show/allow in the UI — the backend independently
// enforces every one of these checks again via 401/403, so a mistake here
// can only ever hide something, never grant real access.

export function isAdmin(user: User | null): boolean {
  return user?.role === "admin";
}

export function isReviewer(user: User | null): boolean {
  return user?.role === "reviewer";
}

export function isSales(user: User | null): boolean {
  return user?.role === "sales";
}

export function hasRole(user: User | null, roles: UserRole[]): boolean {
  if (!user) {
    return false;
  }
  if (user.is_superuser) {
    return true;
  }
  return roles.includes(user.role);
}

export function canViewUsers(user: User | null): boolean {
  return hasRole(user, ["admin"]);
}

export function canViewCRM(user: User | null): boolean {
  return hasRole(user, ["admin", "reviewer", "sales"]);
}

export function canRunSalesWorkflow(user: User | null): boolean {
  return hasRole(user, ["admin", "sales"]);
}

export function canViewWorkflowHistory(user: User | null): boolean {
  return hasRole(user, ["admin", "reviewer", "sales"]);
}

export function canViewResearch(user: User | null): boolean {
  return hasRole(user, ["admin", "reviewer", "sales"]);
}

// Whether the user may set a lead's pipeline_status to any of the seven
// values. Reviewer accounts may still change a lead's pipeline status, but
// only to in_review/approved/rejected (see REVIEWER_PIPELINE_STATUSES in
// app/crm/pipeline/page.tsx) — the backend enforces the same restriction.
export function canSetAnyPipelineStatus(user: User | null): boolean {
  return hasRole(user, ["admin", "sales"]);
}

// Whether the user may open the review-status form at all (email draft
// review status is an admin/reviewer-only backend endpoint — sales is
// blocked entirely, not just from certain values).
export function canManageReviews(user: User | null): boolean {
  return hasRole(user, ["admin", "reviewer"]);
}

// Whether the user may set a review status to "approved"/"rejected"
// specifically. Used to filter Select options on forms that sales may
// otherwise use (e.g. the WorkflowRun review-status form), where the
// backend accepts sales for every status except these two terminal ones.
export function canApproveReviews(user: User | null): boolean {
  return hasRole(user, ["admin", "reviewer"]);
}

// Whether the user may create a new do-not-contact entry. Any logged-in
// user may view the do-not-contact page and run checks; only admin/sales
// may create entries, and only admin may update/deactivate one — the
// backend enforces the identical restrictions.
export function canCreateDoNotContactEntry(user: User | null): boolean {
  return hasRole(user, ["admin", "sales"]);
}

export function canManageDoNotContactEntry(user: User | null): boolean {
  return hasRole(user, ["admin"]);
}

// Whether the user may connect/disconnect their own Gmail/Outlook account
// and create external drafts. Any logged-in user may view integration
// status; only admin/sales may manage a connection or create an external
// draft — the backend enforces the identical restrictions.
export function canManageEmailIntegrationConnection(user: User | null): boolean {
  return hasRole(user, ["admin", "sales"]);
}

export function canCreateExternalEmailDraft(user: User | null): boolean {
  return hasRole(user, ["admin", "sales"]);
}

// Whether the user may view the Reply Inbox at all. Any logged-in user may
// view replies and reply integration status; only admin/sales may trigger
// a sync — the backend enforces the identical restriction.
export function canViewReplies(user: User | null): boolean {
  return hasRole(user, ["admin", "reviewer", "sales"]);
}

export function canSyncReplies(user: User | null): boolean {
  return hasRole(user, ["admin", "sales"]);
}

// Whether the user may view the System Status page (deployment,
// monitoring, backups). Admin-only — the backend enforces the identical
// restriction on every endpoint this page calls.
export function canViewSystemStatus(user: User | null): boolean {
  return hasRole(user, ["admin"]);
}

// Whether the user may view the Compliance Status page. Any logged-in
// admin, sales, or reviewer account — the backend enforces the identical
// restriction on GET /api/v1/compliance/status.
export function canViewComplianceStatus(user: User | null): boolean {
  return hasRole(user, ["admin", "sales", "reviewer"]);
}

// Whether the user may view the Audit Logs page. Admin-only — the backend
// enforces the identical restriction on every audit-log endpoint.
export function canViewAuditLogs(user: User | null): boolean {
  return hasRole(user, ["admin"]);
}
