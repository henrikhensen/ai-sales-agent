"use client";

import { useState } from "react";

import { AgentFormLayout } from "@/components/agents/AgentFormLayout";
import { AgentResultPanel } from "@/components/agents/AgentResultPanel";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { Badge } from "@/components/ui/Badge";
import { ApiError, postJson } from "@/lib/api";
import { emptyToUndefined, linesToList, listToLines } from "@/lib/forms";
import type { EmailDraftRequest, EmailDraftResponse, EmailTone } from "@/lib/types";

const TONE_OPTIONS: { value: EmailTone | ""; label: string }[] = [
  { value: "", label: "Kein Präferenz (Modell entscheidet)" },
  { value: "professional", label: "Professional" },
  { value: "friendly", label: "Friendly" },
  { value: "concise", label: "Concise" },
  { value: "consultative", label: "Consultative" },
];

export default function EmailDraftPage() {
  const [form, setForm] = useState({
    company_name: "Acme GmbH",
    website_url: "https://acme.example.com",
    industry: "Logistics",
    recipient_role: "Leiter Operations",
    recipient_name: "Jane Doe",
    sender_name: "John Smith",
    sender_company: "Beta Vertrieb GmbH",
    product_or_service_offered: "Sendungs-Sichtbarkeitsplattform",
    personalization_summary: "Fokus auf operative Effizienzgewinne.",
    relevant_observations: listToLines(["Kürzliche Expansion in neue Märkte"]),
    pain_point_angles: listToLines(["Mangelnde Sendungstransparenz"]),
    value_arguments: listToLines(["Echtzeit-Tracking reduziert manuelle Nachfragen"]),
    credibility_points: listToLines([
      "Arbeitet mit mittelständischen Frachtdienstleistern",
    ]),
    suggested_ctas: listToLines(["Kurzes 15-minütiges Discovery-Gespräch vorschlagen"]),
    tone: "consultative" as EmailTone | "",
    language: "German",
    notes: "Auf einer Fachmesse kennengelernt.",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<EmailDraftResponse | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const payload: EmailDraftRequest = {
      company_name: form.company_name.trim(),
      website_url: emptyToUndefined(form.website_url),
      industry: emptyToUndefined(form.industry),
      recipient_role: emptyToUndefined(form.recipient_role),
      recipient_name: emptyToUndefined(form.recipient_name),
      sender_name: emptyToUndefined(form.sender_name),
      sender_company: emptyToUndefined(form.sender_company),
      product_or_service_offered: form.product_or_service_offered.trim(),
      personalization_summary: emptyToUndefined(form.personalization_summary),
      relevant_observations: linesToList(form.relevant_observations),
      pain_point_angles: linesToList(form.pain_point_angles),
      value_arguments: linesToList(form.value_arguments),
      credibility_points: linesToList(form.credibility_points),
      suggested_ctas: linesToList(form.suggested_ctas),
      tone: form.tone === "" ? undefined : form.tone,
      language: emptyToUndefined(form.language),
      notes: emptyToUndefined(form.notes),
    };

    try {
      const response = await postJson<EmailDraftResponse>(
        "/api/v1/agents/email-draft",
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
      title="Email Draft Agent"
      description="Erstellt aus Unternehmens-, Lead- und Personalisierungsinformationen einen E-Mail-Entwurf. Dieser Agent sendet keine E-Mails."
      complianceNote="Jeder Entwurf muss von einem Menschen geprüft und freigegeben werden, bevor er verwendet wird."
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
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Empfänger-Rolle"
                value={form.recipient_role}
                onChange={(e) =>
                  setForm({ ...form, recipient_role: e.target.value })
                }
              />
              <Input
                label="Empfänger-Name"
                value={form.recipient_name}
                onChange={(e) =>
                  setForm({ ...form, recipient_name: e.target.value })
                }
              />
            </div>
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
            <Input
              label="Angebotenes Produkt/Service *"
              required
              value={form.product_or_service_offered}
              onChange={(e) =>
                setForm({ ...form, product_or_service_offered: e.target.value })
              }
            />
            <Textarea
              label="Personalisierungs-Zusammenfassung"
              value={form.personalization_summary}
              onChange={(e) =>
                setForm({ ...form, personalization_summary: e.target.value })
              }
            />
            <Textarea
              label="Relevante Beobachtungen (eine Zeile pro Eintrag)"
              value={form.relevant_observations}
              onChange={(e) =>
                setForm({ ...form, relevant_observations: e.target.value })
              }
            />
            <Textarea
              label="Pain-Point-Angles (eine Zeile pro Eintrag)"
              value={form.pain_point_angles}
              onChange={(e) =>
                setForm({ ...form, pain_point_angles: e.target.value })
              }
            />
            <Textarea
              label="Werteargumente (eine Zeile pro Eintrag)"
              value={form.value_arguments}
              onChange={(e) => setForm({ ...form, value_arguments: e.target.value })}
            />
            <Textarea
              label="Glaubwürdigkeitspunkte (eine Zeile pro Eintrag)"
              value={form.credibility_points}
              onChange={(e) =>
                setForm({ ...form, credibility_points: e.target.value })
              }
            />
            <Textarea
              label="Vorgeschlagene CTAs (eine Zeile pro Eintrag)"
              value={form.suggested_ctas}
              onChange={(e) => setForm({ ...form, suggested_ctas: e.target.value })}
            />
            <div className="grid grid-cols-2 gap-4">
              <Select
                label="Tonalität"
                value={form.tone}
                options={TONE_OPTIONS}
                onChange={(e) =>
                  setForm({ ...form, tone: e.target.value as EmailTone | "" })
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
              Entwurf erstellen
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
              {data.subject_lines.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-slate-400">
                    Betreffzeilen
                  </p>
                  <ul className="mt-1 list-inside list-disc text-sm text-slate-700">
                    {data.subject_lines.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              <div>
                <p className="text-xs font-semibold uppercase text-slate-400">
                  E-Mail-Entwurf
                </p>
                <p className="mt-1 whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
                  {data.email_body}
                </p>
              </div>
              {data.do_not_send_if.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-rose-500">
                    Nicht versenden, wenn
                  </p>
                  <ul className="mt-1 list-inside list-disc text-sm text-rose-200">
                    {data.do_not_send_if.map((item) => (
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
