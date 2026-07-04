"use client";

import { useState } from "react";

import { AgentFormLayout } from "@/components/agents/AgentFormLayout";
import { AgentResultPanel } from "@/components/agents/AgentResultPanel";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Badge } from "@/components/ui/Badge";
import { ApiError, postJson } from "@/lib/api";
import { emptyToUndefined } from "@/lib/forms";
import type { LeadResearchRequest, LeadResearchResponse } from "@/lib/types";

const EXAMPLE: LeadResearchRequest = {
  company_name: "Acme GmbH",
  website_url: "https://acme.example.com",
  industry: "Logistics",
  location: "Berlin",
  notes: "Auf einer Fachmesse kennengelernt.",
};

export default function LeadResearchPage() {
  const [form, setForm] = useState({
    company_name: EXAMPLE.company_name,
    website_url: EXAMPLE.website_url ?? "",
    industry: EXAMPLE.industry ?? "",
    location: EXAMPLE.location ?? "",
    notes: EXAMPLE.notes ?? "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LeadResearchResponse | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const payload: LeadResearchRequest = {
      company_name: form.company_name.trim(),
      website_url: emptyToUndefined(form.website_url),
      industry: emptyToUndefined(form.industry),
      location: emptyToUndefined(form.location),
      notes: emptyToUndefined(form.notes),
    };

    try {
      const response = await postJson<LeadResearchResponse>(
        "/api/v1/agents/lead-research",
        payload
      );
      setResult(response);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AgentFormLayout
      title="Lead Research Agent"
      description="Erstellt aus Basisangaben ein erstes Lead-Profil: Zielkunden, Pain Points und mögliche Sales-Angles. Analyse ausschließlich auf Basis der eingegebenen Informationen."
      complianceNote="Der Agent kontaktiert niemanden automatisch und erfindet keine Fakten."
      form={
        <Card title="Eingaben">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <Input
              label="Firmenname *"
              required
              value={form.company_name}
              onChange={(e) => setForm({ ...form, company_name: e.target.value })}
            />
            <Input
              label="Website-URL"
              type="url"
              value={form.website_url}
              onChange={(e) => setForm({ ...form, website_url: e.target.value })}
            />
            <Input
              label="Branche"
              value={form.industry}
              onChange={(e) => setForm({ ...form, industry: e.target.value })}
            />
            <Input
              label="Standort"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
            />
            <Textarea
              label="Notizen"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
            <Button type="submit" loading={loading}>
              Lead analysieren
            </Button>
          </form>
        </Card>
      }
      result={
        <AgentResultPanel
          loading={loading}
          error={error}
          result={result}
          renderSummary={(data) => (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone="info">
                  Confidence: {Math.round(data.confidence_score * 100)}%
                </Badge>
              </div>
              <p className="text-sm text-slate-700">{data.short_summary}</p>
              {data.target_customers.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-slate-400">
                    Zielkunden
                  </p>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-700">
                    {data.target_customers.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {data.likely_pain_points.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-slate-400">
                    Pain Points
                  </p>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-700">
                    {data.likely_pain_points.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          )}
        />
      }
    />
  );
}
