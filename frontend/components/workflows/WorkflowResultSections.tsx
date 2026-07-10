import type { ReactNode } from "react";

import { Badge } from "@/components/ui/Badge";
import type { SalesWorkflowResponse } from "@/lib/types";

interface SectionProps {
  title: string;
  children: ReactNode;
}

function Section({ title, children }: SectionProps) {
  return (
    <div className="border-t border-slate-100 pt-4 first:border-t-0 first:pt-0">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        {title}
      </p>
      <div className="mt-2 space-y-2">{children}</div>
    </div>
  );
}

function StringList({ items, tone }: { items: string[]; tone?: "rose" | "slate" }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">Keine Angaben.</p>;
  }
  const textClass = tone === "rose" ? "text-rose-700" : "text-slate-700";
  return (
    <ul className={`list-inside list-disc text-sm ${textClass}`}>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

const FIT_LEVEL_TONE: Record<string, "positive" | "info" | "warning" | "negative" | "neutral"> = {
  excellent: "positive",
  good: "positive",
  medium: "info",
  weak: "warning",
  not_fit: "negative",
};

const EXTRACTED_TEXT_PREVIEW_LENGTH = 500;

function extractedTextPreview(text: string): string {
  const trimmed = text.trim();
  return trimmed.length > EXTRACTED_TEXT_PREVIEW_LENGTH
    ? `${trimmed.slice(0, EXTRACTED_TEXT_PREVIEW_LENGTH)}…`
    : trimmed;
}

interface WorkflowResultSectionsProps {
  data: SalesWorkflowResponse;
}

export function WorkflowResultSections({ data }: WorkflowResultSectionsProps) {
  return (
    <div className="space-y-4">
      <Section title="Workflow-Status">
        <div className="flex flex-wrap items-center gap-2">
          <Badge tone={data.status === "completed" ? "positive" : "warning"}>
            {data.status}
          </Badge>
          <Badge tone={data.human_review_required ? "warning" : "neutral"}>
            {data.human_review_required
              ? "Menschliche Prüfung erforderlich"
              : "Keine Prüfung markiert"}
          </Badge>
          <Badge tone="info">
            Confidence gesamt: {Math.round(data.confidence_score * 100)}%
          </Badge>
        </div>
        <p className="text-xs text-slate-500">Workflow-ID: {data.workflow_id}</p>
      </Section>

      {data.do_not_contact_block?.is_blocked ? (
        <Section title="Do-not-contact">
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
            <p className="font-medium">
              Do-not-contact blockiert Outreach — kein Email Draft wurde erstellt.
            </p>
            <p className="mt-1">
              Matched by: {data.do_not_contact_block.matched_by}
            </p>
            {data.do_not_contact_block.reason ? (
              <p>Reason: {data.do_not_contact_block.reason}</p>
            ) : null}
          </div>
        </Section>
      ) : null}

      <Section title="Lead Research">
        <p className="text-sm text-slate-700">{data.lead_research.short_summary}</p>
        <p className="text-xs font-medium text-slate-500">Zielkunden</p>
        <StringList items={data.lead_research.target_customers} />
        <p className="text-xs font-medium text-slate-500">Pain Points</p>
        <StringList items={data.lead_research.likely_pain_points} />
      </Section>

      <Section title="Company Intelligence">
        <p className="text-sm text-slate-700">
          {data.company_intelligence.business_summary}
        </p>
        <p className="text-sm text-slate-700">
          {data.company_intelligence.positioning_summary}
        </p>
        <p className="text-xs font-medium text-slate-500">Value Proposition</p>
        <StringList items={data.company_intelligence.value_proposition} />
      </Section>

      {data.icp_profile_id ? (
        <Section title="ICP Fit">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={FIT_LEVEL_TONE[data.icp_fit_level ?? ""] ?? "neutral"}>
              {data.icp_fit_level ?? "unbekannt"}
            </Badge>
            <span className="text-sm text-slate-700">
              Fit Score: {data.icp_fit_score ?? "—"} / 100
            </span>
          </div>
          {data.icp_fit_summary ? (
            <p className="text-sm text-slate-700">{data.icp_fit_summary}</p>
          ) : null}
          {data.icp_warnings.length > 0 ? (
            <>
              <p className="text-xs font-medium text-slate-500">Warnings</p>
              <StringList items={data.icp_warnings} tone="rose" />
            </>
          ) : null}
        </Section>
      ) : null}

      {data.offer_profile_id ? (
        <Section title="Offer">
          {data.offer_summary ? (
            <p className="text-sm text-slate-700">{data.offer_summary}</p>
          ) : null}
          {data.offer_warnings.length > 0 ? (
            <>
              <p className="text-xs font-medium text-slate-500">Warnings</p>
              <StringList items={data.offer_warnings} tone="rose" />
            </>
          ) : null}
        </Section>
      ) : null}

      {data.website_research || data.website_research_warnings.length > 0 ? (
        <Section title="Website Research">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={data.website_research_used ? "positive" : "neutral"}>
              {data.website_research_used
                ? "Website Research verwendet"
                : "Website Research nicht verwendet"}
            </Badge>
          </div>
          {!data.website_research_used ? (
            <p className="text-sm text-slate-600">
              Website Research wurde nicht verwendet oder konnte nicht
              erfolgreich abgeschlossen werden.
            </p>
          ) : null}
          {data.website_research_warnings.length > 0 ? (
            <>
              <p className="text-xs font-medium text-slate-500">Warnings</p>
              <StringList items={data.website_research_warnings} tone="rose" />
            </>
          ) : null}
          {data.website_research ? (
            <>
              <p className="text-xs font-medium text-slate-500">
                Gefundene Informationen
              </p>
              <dl className="space-y-1 text-sm">
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Domain</dt>
                  <dd className="font-mono text-slate-900">
                    {data.website_research.domain}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Title</dt>
                  <dd className="text-right text-slate-900">
                    {data.website_research.title ?? "—"}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Meta Description</dt>
                  <dd className="text-right text-slate-900">
                    {data.website_research.meta_description ?? "—"}
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Text Length</dt>
                  <dd className="text-slate-900">
                    {data.website_research.text_length} Zeichen
                  </dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Pages Fetched</dt>
                  <dd className="text-slate-900">
                    {data.website_research.pages_fetched}
                  </dd>
                </div>
              </dl>
              <p className="text-xs font-medium text-slate-500">Sources Used</p>
              <ul className="space-y-1">
                {data.website_research.sources_used.map((source) => (
                  <li key={source} className="break-all font-mono text-xs text-slate-700">
                    {source}
                  </li>
                ))}
              </ul>
              <p className="text-xs font-medium text-slate-500">
                Extracted Text (Vorschau)
              </p>
              <p className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
                {extractedTextPreview(data.website_research.extracted_text)}
              </p>
            </>
          ) : null}
        </Section>
      ) : null}

      {data.personalization ? (
        <Section title="Personalization">
          <p className="text-sm text-slate-700">
            {data.personalization.personalization_summary}
          </p>
          <p className="text-xs font-medium text-slate-500">Vorgeschlagene CTAs</p>
          <StringList items={data.personalization.suggested_ctas} />
          <p className="text-xs font-medium text-slate-500">Nicht verwenden</p>
          <StringList items={data.personalization.do_not_use_claims} tone="rose" />
        </Section>
      ) : null}

      {data.email_draft ? (
        <Section title="Draft zur Prüfung (nur Entwurf, kein Versand)">
          <p className="text-xs font-medium text-slate-500">Betreffzeilen</p>
          <StringList items={data.email_draft.subject_lines} />
          <p className="text-xs font-medium text-slate-500">E-Mail-Entwurf</p>
          <p className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
            {data.email_draft.email_body}
          </p>
          <p className="text-xs font-medium text-slate-500">
            Vor Versand zu prüfende Aussagen
          </p>
          <StringList items={data.email_draft.claims_to_verify} tone="rose" />
          <p className="text-xs font-medium text-slate-500">
            Nicht versenden, wenn
          </p>
          <StringList items={data.email_draft.do_not_send_if} tone="rose" />
        </Section>
      ) : null}

      {data.crm_company_id || data.crm_lead_id || data.crm_email_draft_id ? (
        <Section title="CRM gespeichert">
          <p className="text-sm text-slate-600">
            Diese CRM-Verknüpfungen wurden automatisch gespeichert. Es wurde
            keine E-Mail gesendet.
          </p>
          <dl className="mt-2 space-y-1 text-sm">
            {data.crm_company_id ? (
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Company ID</dt>
                <dd className="font-mono text-slate-900">{data.crm_company_id}</dd>
              </div>
            ) : null}
            {data.crm_lead_id ? (
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Lead ID</dt>
                <dd className="font-mono text-slate-900">{data.crm_lead_id}</dd>
              </div>
            ) : null}
            {data.crm_email_draft_id ? (
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Email Draft ID</dt>
                <dd className="font-mono text-slate-900">{data.crm_email_draft_id}</dd>
              </div>
            ) : null}
          </dl>
          <p className="mt-2 text-xs text-slate-500">
            Der E-Mail-Entwurf wurde nur gespeichert, nicht versendet.
          </p>
        </Section>
      ) : null}

      <Section title="Human Review Checklist">
        <StringList items={data.review_checklist} />
      </Section>

      <Section title="Compliance Notes">
        <StringList items={data.compliance_notes} />
      </Section>

      <Section title="Fehlende Informationen">
        <StringList items={data.missing_information} />
      </Section>
    </div>
  );
}
