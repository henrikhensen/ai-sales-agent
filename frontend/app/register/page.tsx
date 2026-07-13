"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { ApiError } from "@/lib/api";
import type { UserRole } from "@/lib/types";

const ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: "sales", label: "Sales" },
  { value: "reviewer", label: "Reviewer" },
  { value: "admin", label: "Admin" },
];

export default function RegisterPage() {
  const { register, login, isAuthenticated } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<UserRole>("sales");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/");
    }
  }, [isAuthenticated, router]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(false);
    try {
      await register({
        email,
        password,
        full_name: fullName.trim() || undefined,
        role,
      });
      setSuccess(true);
      await login({ email, password });
      router.replace("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Registrieren</h1>
        <p className="mt-1 text-sm text-slate-600">
          Neues lokales Benutzerkonto anlegen.
        </p>
      </div>

      <div className="rounded-lg border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
        <ul className="list-inside list-disc space-y-0.5">
          <li>Lokale Authentifizierung für MVP.</li>
          <li>Keine externen Auth Provider.</li>
          <li>Kein automatischer Versand oder Outreach.</li>
        </ul>
      </div>

      <Card>
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
            label="Passwort * (mind. 8 Zeichen)"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
          />
          <Input
            label="Name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            autoComplete="name"
          />
          <Select
            label="Rolle"
            value={role}
            options={ROLE_OPTIONS}
            onChange={(e) => setRole(e.target.value as UserRole)}
          />
          <Button type="submit" loading={loading} className="w-full justify-center">
            Registrieren
          </Button>
          {success ? (
            <p className="text-sm text-emerald-200">
              Konto erstellt. Du wirst angemeldet…
            </p>
          ) : null}
          {error ? (
            <div className="rounded-lg border border-rose-400/25 bg-rose-400/10 px-3 py-2 text-sm text-rose-200">
              {error}
            </div>
          ) : null}
        </form>
        <p className="mt-4 text-sm text-slate-600">
          Bereits ein Konto?{" "}
          <Link href="/login" className="font-medium text-brand-600 hover:text-brand-700">
            Anmelden
          </Link>
        </p>
      </Card>
    </div>
  );
}
