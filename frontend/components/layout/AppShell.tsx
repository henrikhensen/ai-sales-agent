"use client";

import { usePathname } from "next/navigation";
import { useState, type ReactNode } from "react";

import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { ToastProvider } from "@/components/ui/ToastProvider";

interface AppShellProps {
  children: ReactNode;
}

// Auth routes are reachable before a session exists, so they must never
// look like "the internal app minus a login" — a visitor's very first
// impression of the product is one of these two pages. No Sidebar (there
// is nothing to navigate to yet), a clean centered panel, and the same
// ambient dark-canvas motion as the Home hero instead of the dense
// internal chrome.
const AUTH_ROUTES = new Set(["/login", "/register"]);

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  if (AUTH_ROUTES.has(pathname)) {
    return (
      <ToastProvider>
        <div className="flex min-h-screen flex-col bg-canvas">
          <Header onMenuClick={() => {}} showMenuButton={false} />
          <main className="relative flex flex-1 items-center justify-center overflow-hidden px-4 py-16">
            <div
              className="pointer-events-none absolute -left-32 -top-32 h-[24rem] w-[24rem] rounded-full bg-surface opacity-60 blur-3xl motion-safe:animate-drift-a"
              aria-hidden="true"
            />
            <div
              className="pointer-events-none absolute -bottom-32 -right-24 h-[22rem] w-[22rem] rounded-full bg-muted/10 blur-3xl motion-safe:animate-drift-b"
              aria-hidden="true"
            />
            <div className="relative w-full max-w-md">{children}</div>
          </main>
        </div>
      </ToastProvider>
    );
  }

  return (
    <ToastProvider>
      <div className="flex min-h-screen">
        <div className="hidden md:block">
          <Sidebar />
        </div>

        {mobileNavOpen ? (
          <div className="fixed inset-0 z-40 flex md:hidden">
            <div
              className="fixed inset-0 bg-canvas/70 backdrop-blur-sm"
              onClick={() => setMobileNavOpen(false)}
              aria-hidden="true"
            />
            <div className="relative z-50">
              <Sidebar onNavigate={() => setMobileNavOpen(false)} />
            </div>
          </div>
        ) : null}

        <div className="flex min-h-screen flex-1 flex-col">
          <Header onMenuClick={() => setMobileNavOpen(true)} />
          <main className="flex-1 bg-canvas px-4 py-6 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-7xl">{children}</div>
          </main>
        </div>
      </div>
    </ToastProvider>
  );
}
