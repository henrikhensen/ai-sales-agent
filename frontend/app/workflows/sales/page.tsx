"use client";

import { useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { AgentFormLayout } from "@/components/agents/AgentFormLayout";
import { AgentResultPanel } from "@/components/agents/AgentResultPanel";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ComplianceNotice } from "@/components/ui/ComplianceNotice";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { WorkflowResultSections } from "@/components/workflows/WorkflowResultSections";
import { ApiError, runSalesWorkflow } from "@/lib/api";
import { emptyToUndefined } from "@/lib/forms";
import type { EmailTone, SalesWorkflowRequest, SalesWorkflowResponse } from "@/lib/types";

const TONE_OPTIONS: { value: EmailTone; label: string }[] = [
  { value: "professional", label: "Professional" },
  { value: "friendly", label: "Friendly" },
  { value: "concise", label: "Concise" },
  { value: "consultative", label: "Consultative" },
];

const MAX_PAGES_OPTIONS = [
  { value: "1", label: "1 Seite" },
  { value: "2", label: "2 Seiten" },
  { value: "3", label: "3 Seiten" },
];

export default function SalesWorkflowPage() {
  const [form, setForm] = useState({
    company_name: "Acme GmbH",
    website_url: "https://acme.example.com",
    industry: "Logistics",
    location: "Berlin",
    company_description: "B2B-Logistikdienstleister mit Fokus auf Mittelstand.",
    website_text: "",
    target_persona: "Leiter Operations",
    product_or_service_offered: "Sendungs-Sichtbarkeitsplattform",
    sender_name: "John Smith",
    sender_company: "Beta Vertrieb GmbH",
    tone: "professional" as EmailTone,
    language: "German",
    notes: "Auf einer Fachmesse kennengelernt.",
    use_website_research: false,
    website_research_max_pages: "1",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SalesWorkflowResponse | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (form.use_website_research && !form.website_url.trim()) {
      setError(
        "Website-URL ist erforderlich, wenn Website Research aktiviert ist."
      );
      return;
    }

    setLoading(true);
    setResult(null);

    const payload: SalesWorkflowRequest = {
      company_name: form.company_name.trim(),
      website_url: emptyToUndefined(form.website_url),
      industry: emptyToUndefined(form.industry),
      location: emptyToUndefined(form.location),
      company_description: emptyToUndefined(form.company_description),
      website_text: emptyToUndefined(form.website_text),
      target_persona: emptyToUndefined(form.target_persona),
      product_or_service_offered: form.product_or_service_offered.trim(),
      sender_name: emptyToUndefined(form.sender_name),
      sender_company: emptyToUndefined(form.sender_company),
      tone: form.tone,
      language: emptyToUndefined(form.language),
      notes: emptyToUndefined(form.notes),
      use_website_research: form.use_website_research,
      website_research_max_pages: Number(form.website_research_max_pages),
    };

    try {
      const response = await runSalesWorkflow(payload);
      setResult(response);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unerwarteter Fehler.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <RequireRole
      allowedRoles={["admin", "sales"]}
      deniedMessage="Nur Admin und Sales dürfen den Sales Workflow starten."
    >
    <div className="space-y-6">
      <ComplianceNotice>
        Nach erfolgreichem Lauf werden Company, Lead und Email Draft
        automatisch im CRM gespeichert.
      </ComplianceNotice>
      <AgentFormLayout
        title="Sales Workflow"
        description="Führt Lead Research, Company Intelligence, Personalization und Email Draft nacheinander aus und fasst das Ergebnis für eine menschliche Prüfung zusammen."
        complianceNote="Dieser Workflow sendet keine E-Mails. Der E-Mail-Text ist nur ein Entwurf. Menschliche Prüfung ist für jede Aktion erforderlich, bevor irgendetwas passiert."
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
              hint={
                form.use_website_research
                  ? "Erforderlich, solange Website Research aktiviert ist."
                  : undefined
              }
            />
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <label className="flex items-start gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  className="mt-0.5 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500"
                  checked={form.use_website_research}
                  onChange={(e) =>
                    setForm({ ...form, use_website_research: e.target.checked })
                  }
                />
                <span>
                  Website Research verwenden
                  <span className="block text-xs text-slate-500">
                    Ruft die oben angegebene Website-URL ab und nutzt den
                    extrahierten Text als Kontext für Company Intelligence.
                  </span>
                </span>
              </label>
              {form.use_website_research ? (
                <div className="mt-3 max-w-xs">
                  <Select
                    label="Max Pages"
                    value={form.website_research_max_pages}
                    options={MAX_PAGES_OPTIONS}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        website_research_max_pages: e.target.value,
                      })
                    }
                    hint="Reserviert für ein späteres Crawling — aktuell wird immer nur die angegebene URL abgerufen."
                  />
                </div>
              ) : null}
              <ul className="mt-3 list-inside list-disc space-y-0.5 text-xs text-slate-500">
                <li>Website Research ruft nur die angegebene öffentliche URL ab.</li>
                <li>Kein LinkedIn Scraping.</li>
                <li>Kein LLM Call durch Website Research.</li>
                <li>Keine E-Mail wird versendet.</li>
                <li>Keine automatische Kontaktaufnahme.</li>
              </ul>
            </div>
            <div className="grid grid-cols-2 gap-4">
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
            </div>
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
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Absender-Name"
                value={form.sender_name}
                onChange={(e) => setForm({ ...form, sender_name: e.target.value })}
              />
              <Input
                label="Absender-Firma"
                value={form.sender_company}
                onChange={(e) =>
                  setForm({ ...form, sender_company: e.target.value })
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <Select
                label="Tonalität"
                value={form.tone}
                options={TONE_OPTIONS}
                onChange={(e) =>
                  setForm({ ...form, tone: e.target.value as EmailTone })
                }
              />
              <Input
                label="Sprache"
                value={form.language}
                onChange={(e) => setForm({ ...form, language: e.target.value })}
              />
            </div>
            <Textarea
              label="Notizen"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
            <Button type="submit" loading={loading}>
              Workflow starten
            </Button>
          </form>
        </Card>
        }
        result={
          <AgentResultPanel
            loading={loading}
            error={error}
            result={result}
            emptyHint="Noch kein Workflow gestartet."
            renderSummary={(data) => <WorkflowResultSections data={data} />}
          />
        }
      />
    </div>
    </RequireRole>
  );
}
