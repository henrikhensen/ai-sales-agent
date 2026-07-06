"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/components/auth/AuthProvider";

interface RequireAuthProps {
  children: ReactNode;
}

/**
 * Wraps a protected page: redirects to /login if no user is logged in.
 *
 * Waits for the initial auth check (``loading``) before deciding, so a
 * logged-in user never sees a flash-redirect to /login on page load. If the
 * backend's ``/auth/me`` returned 401 (e.g. an expired token), the
 * ``AuthProvider`` already cleared the token before this ever renders.
 */
export function RequireAuth({ children }: RequireAuthProps) {
  const { isAuthenticated, loading } = useAuth();
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

  return <>{children}</>;
}
