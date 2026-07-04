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
import { emptyToUndefined, linesToList, listToLines } from "@/lib/forms";
import type {
  CompanyIntelligenceRequest,
  CompanyIntelligenceResponse,
} from "@/lib/types";

export default function CompanyIntelligencePage() {
  const [form, setForm] = useState({
    company_name: "HubSpot",
    website_url: "https://www.hubspot.com",
    industry: "CRM Software",
    location: "USA",
    company_description: "B2B SaaS für Marketing, Sales und Service.",
    website_text: "",
    known_products: listToLines(["Marketing Hub", "Sales Hub"]),
    known_customers: listToLines(["KMU"]),
    notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CompanyIntelligenceResponse | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const payload: CompanyIntelligenceRequest = {
      company_name: form.company_name.trim(),
      website_url: emptyToUndefined(form.website_url),
      industry: emptyToUndefined(form.industry),
      location: emptyToUndefined(form.location),
      company_description: emptyToUndefined(form.company_description),
      website_text: emptyToUndefined(form.website_text),
      known_products: linesToList(form.known_products),
      known_customers: linesToList(form.known_customers),
      notes: emptyToUndefined(form.notes),
    };

    try {
      const response = await postJson<CompanyIntelligenceResponse>(
        "/api/v1/agents/company-intelligence",
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
      title="Company Intelligence Agent"
      description="Erstellt eine tiefere, strategische Unternehmensanalyse: Positionierung, Buyer Personas, Value Proposition und Sales-Relevanz."
      complianceNote="Wettbewerber werden nur genannt, wenn sie im Input erwähnt wurden. Keine erfundenen Fakten."
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
              label="Unternehmensbeschreibung"
              value={form.company_description}
              onChange={(e) =>
                setForm({ ...form, company_description: e.target.value })
              }
            />
            <Textarea
              label="Website-Text"
              value={form.website_text}
              onChange={(e) => setForm({ ...form, website_text: e.target.value })}
            />
            <Textarea
              label="Bekannte Produkte (eine Zeile pro Eintrag)"
              value={form.known_products}
              onChange={(e) => setForm({ ...form, known_products: e.target.value })}
            />
            <Textarea
              label="Bekannte Kunden (eine Zeile pro Eintrag)"
              value={form.known_customers}
              onChange={(e) => setForm({ ...form, known_customers: e.target.value })}
            />
            <Textarea
              label="Notizen"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
            <Button type="submit" loading={loading}>
              Unternehmen analysieren
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
              <Badge tone="info">
                Confidence: {Math.round(data.confidence_score * 100)}%
              </Badge>
              <p className="text-sm text-slate-700">{data.business_summary}</p>
              <p className="text-sm text-slate-700">{data.positioning_summary}</p>
              {data.value_proposition.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-slate-400">
                    Value Proposition
                  </p>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-700">
                    {data.value_proposition.map((item) => (
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
