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

      <Section title="Personalization">
        <p className="text-sm text-slate-700">
          {data.personalization.personalization_summary}
        </p>
        <p className="text-xs font-medium text-slate-500">Vorgeschlagene CTAs</p>
        <StringList items={data.personalization.suggested_ctas} />
        <p className="text-xs font-medium text-slate-500">Nicht verwenden</p>
        <StringList items={data.personalization.do_not_use_claims} tone="rose" />
      </Section>

      <Section title="Email Draft (nur Entwurf, wird nicht versendet)">
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
