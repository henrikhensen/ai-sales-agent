import type { ReactNode } from "react";

interface ComplianceNoticeProps {
  children?: ReactNode;
}

export function ComplianceNotice({ children }: ComplianceNoticeProps) {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
      {children ? <p>{children}</p> : null}
      <ul
        className={`list-inside list-disc space-y-0.5 ${children ? "mt-2" : ""}`}
      >
        <li>Keine automatische Kontaktaufnahme.</li>
        <li>Email Drafts sind nur Entwürfe.</li>
        <li>Review Status löst keinen Versand aus.</li>
        <li>Mock-Modus aktiv.</li>
      </ul>
    </div>
  );
}
