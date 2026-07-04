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
import type { PersonalizationRequest, PersonalizationResponse } from "@/lib/types";

export default function PersonalizationPage() {
  const [form, setForm] = useState({
    company_name: "Acme GmbH",
    website_url: "https://acme.example.com",
    industry: "Logistics",
    location: "Berlin",
    lead_summary: "Logistikunternehmen mit Sitz in Berlin.",
    company_intelligence_summary: "Mittelständischer Frachtdienstleister.",
    target_persona: "Leiter Operations",
    product_or_service_offered: "Sendungs-Sichtbarkeitsplattform",
    value_proposition: "Echtzeit-Tracking von Sendungen.",
    known_pain_points: listToLines(["Mangelnde Sendungstransparenz"]),
    known_triggers: listToLines(["Kürzliche Expansion in neue Märkte"]),
    notes: "Auf einer Fachmesse kennengelernt.",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PersonalizationResponse | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const payload: PersonalizationRequest = {
      company_name: form.company_name.trim(),
      website_url: emptyToUndefined(form.website_url),
      industry: emptyToUndefined(form.industry),
      location: emptyToUndefined(form.location),
      lead_summary: emptyToUndefined(form.lead_summary),
      company_intelligence_summary: emptyToUndefined(
        form.company_intelligence_summary
      ),
      target_persona: emptyToUndefined(form.target_persona),
      product_or_service_offered: form.product_or_service_offered.trim(),
      value_proposition: emptyToUndefined(form.value_proposition),
      known_pain_points: linesToList(form.known_pain_points),
      known_triggers: linesToList(form.known_triggers),
      notes: emptyToUndefined(form.notes),
    };

    try {
      const response = await postJson<PersonalizationResponse>(
        "/api/v1/agents/personalization",
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
      title="Personalization Engine"
      description="Erstellt aus Unternehmens-, Lead- und Analyseinformationen eine strukturierte Personalisierungsstrategie für einen menschlichen Sales-Mitarbeiter."
      complianceNote="Liefert Vorschläge, keine fertige Outreach-Nachricht. Keine automatische Kontaktaufnahme."
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
              label="Lead-Research-Zusammenfassung"
              value={form.lead_summary}
              onChange={(e) => setForm({ ...form, lead_summary: e.target.value })}
            />
            <Textarea
              label="Company-Intelligence-Zusammenfassung"
              value={form.company_intelligence_summary}
              onChange={(e) =>
                setForm({ ...form, company_intelligence_summary: e.target.value })
              }
            />
            <Input
              label="Ziel-Persona"
              value={form.target_persona}
              onChange={(e) => setForm({ ...form, target_persona: e.target.value })}
            />
            <Input
              label="Angebotenes Produkt/Service *"
              required
              value={form.product_or_service_offered}
              onChange={(e) =>
                setForm({ ...form, product_or_service_offered: e.target.value })
              }
            />
            <Textarea
              label="Value Proposition"
              value={form.value_proposition}
              onChange={(e) =>
                setForm({ ...form, value_proposition: e.target.value })
              }
            />
            <Textarea
              label="Bekannte Pain Points (eine Zeile pro Eintrag)"
              value={form.known_pain_points}
              onChange={(e) =>
                setForm({ ...form, known_pain_points: e.target.value })
              }
            />
            <Textarea
              label="Bekannte Trigger (eine Zeile pro Eintrag)"
              value={form.known_triggers}
              onChange={(e) => setForm({ ...form, known_triggers: e.target.value })}
            />
            <Textarea
              label="Notizen"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
            <Button type="submit" loading={loading}>
              Strategie erstellen
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
              <p className="text-sm text-slate-700">{data.personalization_summary}</p>
              {data.suggested_ctas.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-slate-400">
                    Vorgeschlagene CTAs
                  </p>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-700">
                    {data.suggested_ctas.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {data.do_not_use_claims.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-rose-500">
                    Nicht verwenden
                  </p>
                  <ul className="mt-1 list-inside list-disc text-sm text-rose-700">
                    {data.do_not_use_claims.map((item) => (
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
