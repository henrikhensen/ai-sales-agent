import type { ReactNode } from "react";

interface ComplianceNoticeProps {
  children?: ReactNode;
}

export function ComplianceNotice({ children }: ComplianceNoticeProps) {
  return (
    <div className="rounded-none border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm text-amber-200">
      {children ? <p>{children}</p> : null}
      <ul
        className={`list-inside list-disc space-y-0.5 ${children ? "mt-2" : ""}`}
      >
        <li>Keine automatische Kontaktaufnahme.</li>
        <li>Email Drafts sind nur Entwürfe.</li>
        <li>Review Status löst keinen Versand aus.</li>
        <li>Approval bedeutet keine Versandfreigabe.</li>
        <li>Menschliche Prüfung bleibt erforderlich.</li>
        <li>Mock-Modus aktiv.</li>
      </ul>
    </div>
  );
}
