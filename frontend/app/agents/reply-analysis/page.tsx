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
import type {
  ReplyAnalysisRequest,
  ReplyAnalysisResponse,
  ReplySentiment,
} from "@/lib/types";

const SENTIMENT_TONE: Record<ReplySentiment, "positive" | "negative" | "neutral"> = {
  positive: "positive",
  negative: "negative",
  neutral: "neutral",
  unclear: "neutral",
};

export default function ReplyAnalysisPage() {
  const [form, setForm] = useState({
    company_name: "Acme GmbH",
    lead_name: "Jane Doe",
    lead_role: "Leiter Operations",
    original_email_subject: "Mehr Transparenz in Ihrer Sendungslogistik",
    original_email_body: "Hallo Frau Doe, ...",
    reply_text:
      "Danke für die Nachricht. Können wir nächste Woche kurz telefonieren?",
    previous_context: "Erstkontakt vor zwei Wochen.",
    product_or_service_offered: "Sendungs-Sichtbarkeitsplattform",
    notes: "Wirkt interessiert.",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ReplyAnalysisResponse | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    const payload: ReplyAnalysisRequest = {
      company_name: form.company_name.trim(),
      lead_name: emptyToUndefined(form.lead_name),
      lead_role: emptyToUndefined(form.lead_role),
      original_email_subject: emptyToUndefined(form.original_email_subject),
      original_email_body: emptyToUndefined(form.original_email_body),
      reply_text: form.reply_text.trim(),
      previous_context: emptyToUndefined(form.previous_context),
      product_or_service_offered: emptyToUndefined(
        form.product_or_service_offered
      ),
      notes: emptyToUndefined(form.notes),
    };

    try {
      const response = await postJson<ReplyAnalysisResponse>(
        "/api/v1/agents/reply-analysis",
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
      title="Reply Analysis Agent"
      description="Klassifiziert eingehende Antworten von Leads und liefert strukturierte Handlungsvorschläge für einen menschlichen Sales-Mitarbeiter."
      complianceNote="Es wird keine Antwort automatisch gesendet und kein Termin automatisch gebucht. Bei Desinteresse empfiehlt der Agent eine respektvolle Beendigung."
      form={
        <Card title="Eingaben">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <Input
              label="Firmenname *"
              required
              value={form.company_name}
              onChange={(e) => setForm({ ...form, company_name: e.target.value })}
            />
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Lead-Name"
                value={form.lead_name}
                onChange={(e) => setForm({ ...form, lead_name: e.target.value })}
              />
              <Input
                label="Lead-Rolle"
                value={form.lead_role}
                onChange={(e) => setForm({ ...form, lead_role: e.target.value })}
              />
            </div>
            <Input
              label="Betreff der Original-E-Mail"
              value={form.original_email_subject}
              onChange={(e) =>
                setForm({ ...form, original_email_subject: e.target.value })
              }
            />
            <Textarea
              label="Original-E-Mail (Text)"
              value={form.original_email_body}
              onChange={(e) =>
                setForm({ ...form, original_email_body: e.target.value })
              }
            />
            <Textarea
              label="Antworttext *"
              required
              value={form.reply_text}
              onChange={(e) => setForm({ ...form, reply_text: e.target.value })}
            />
            <Textarea
              label="Bisheriger Kontext"
              value={form.previous_context}
              onChange={(e) =>
                setForm({ ...form, previous_context: e.target.value })
              }
            />
            <Input
              label="Angebotenes Produkt/Service"
              value={form.product_or_service_offered}
              onChange={(e) =>
                setForm({ ...form, product_or_service_offered: e.target.value })
              }
            />
            <Textarea
              label="Notizen"
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
            <Button type="submit" loading={loading}>
              Antwort analysieren
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
                <Badge tone="info">{data.classification}</Badge>
                <Badge tone={SENTIMENT_TONE[data.sentiment]}>{data.sentiment}</Badge>
                <Badge tone="warning">Dringlichkeit: {data.urgency}</Badge>
                <Badge tone="neutral">
                  Confidence: {Math.round(data.confidence_score * 100)}%
                </Badge>
              </div>
              <p className="text-sm text-slate-700">{data.summary}</p>
              <div>
                <p className="text-xs font-semibold uppercase text-slate-400">
                  Empfohlene nächste Aktion
                </p>
                <p className="text-sm text-slate-700">
                  {data.recommended_next_action}
                </p>
              </div>
              {data.suggested_reply ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-slate-400">
                    Antwortentwurf (nur Vorschlag)
                  </p>
                  <p className="mt-1 whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
                    {data.suggested_reply}
                  </p>
                </div>
              ) : null}
              {data.do_not_continue_if.length > 0 ? (
                <div>
                  <p className="text-xs font-semibold uppercase text-rose-500">
                    Keine weitere Kontaktaufnahme, wenn
                  </p>
                  <ul className="mt-1 list-inside list-disc text-sm text-rose-200">
                    {data.do_not_continue_if.map((item) => (
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
