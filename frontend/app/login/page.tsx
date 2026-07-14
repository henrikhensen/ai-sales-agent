"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/");
    }
  }, [isAuthenticated, router]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login({ email, password });
      router.replace("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="animate-fade-in-up">
      <div className="mb-8 text-center">
        <span className="mono-label">AI Sales Copilot</span>
        <h1 className="mt-3 text-3xl font-black tracking-tight text-muted">Willkommen zurück.</h1>
        <p className="mt-2 text-sm text-muted/60">Mit E-Mail und Passwort anmelden.</p>
      </div>

      <Card variant="framed">
        <form className="space-y-4" onSubmit={handleSubmit}>
          <Input
            label="E-Mail *"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
          <Input
            label="Passwort *"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
          <Button type="submit" loading={loading} className="w-full justify-center">
            Anmelden
          </Button>
          {error ? (
            <div className="border-l-4 border-l-rose-500 bg-rose-400/5 py-2 pl-3 text-sm text-rose-200">
              {error}
            </div>
          ) : null}
        </form>
        <p className="mt-4 text-sm text-muted/60">
          Noch kein Konto?{" "}
          <Link href="/register" className="font-semibold text-muted underline underline-offset-2 hover:text-muted/70">
            Registrieren
          </Link>
        </p>
      </Card>

      <p className="mt-6 text-center text-xs text-muted/40">
        Lokale Authentifizierung, kein externer Auth-Provider — kein automatischer Versand oder Outreach.
      </p>
    </div>
  );
}
