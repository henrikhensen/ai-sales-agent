"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { AccessDenied } from "@/components/auth/AccessDenied";
import { useAuth } from "@/components/auth/AuthProvider";
import { hasRole } from "@/lib/roles";
import type { UserRole } from "@/lib/types";

interface RequireRoleProps {
  allowedRoles: UserRole[];
  children: ReactNode;
  deniedMessage?: string;
}

/**
 * Wraps a protected page: redirects to /login if no user is logged in
 * (same as RequireAuth), and renders an Access Denied panel — no redirect,
 * no logout — if the logged-in user's role is not in ``allowedRoles``.
 *
 * Waits for the initial auth check (``loading``) before deciding, so a
 * logged-in user never sees a flash-redirect to /login on page load, and
 * never bounces between /login and the page (no redirect loop): once
 * ``isAuthenticated`` is true, the only other outcome is either the page
 * itself or the Access Denied panel — neither of which redirects again.
 */
export function RequireRole({ allowedRoles, children, deniedMessage }: RequireRoleProps) {
  const { currentUser, isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [loading, isAuthenticated, router]);

  if (loading) {
    return <p className="text-sm text-slate-500">Lade…</p>;
  }

  if (!isAuthenticated) {
    return null;
  }

  if (!hasRole(currentUser, allowedRoles)) {
    return <AccessDenied message={deniedMessage} />;
  }

  return <>{children}</>;
}
