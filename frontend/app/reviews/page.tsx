import Link from "next/link";

import { RequireRole } from "@/components/auth/RequireRole";
import { Card } from "@/components/ui/Card";
import { ComplianceNotice } from "@/components/ui/ComplianceNotice";

export default function ReviewsPage() {
  return (
    <RequireRole
      allowedRoles={["admin", "reviewer"]}
      deniedMessage="Nur Admin und Reviewer haben Zugriff auf Human Review. Sales sieht Kommentare direkt in der Workflow History."
    >
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Human Review</h1>
        <p className="mt-1 text-sm text-slate-600">
          Übersicht über den Human-Review-Prozess für Email Drafts und
          Workflow Runs.
        </p>
      </div>

      <ComplianceNotice />

      <Card title="Wie Human Review funktioniert">
        <div className="space-y-3 text-sm text-slate-700">
          <p>
            Jeder Sales Workflow erzeugt CRM-Daten und einen Email-Entwurf,
            die von einem Menschen geprüft werden müssen, bevor irgendetwas
            passiert. Dieses System sendet selbst nie eine E-Mail und nimmt
            nie automatisch Kontakt auf — Approval ist ausschließlich eine
            interne Freigabe.
          </p>
          <ol className="list-inside list-decimal space-y-1">
            <li>
              Workflow Run in der Workflow History öffnen, Ergebnis prüfen
              und optional einen Kommentar hinterlassen.
            </li>
            <li>
              Email Draft in der CRM-Übersicht öffnen, Review Status setzen
              und optional Reviewer-Name und Kommentar hinzufügen.
            </li>
            <li>
              Audit Timeline ansehen, um alle Review-Ereignisse (Status
              geändert, Kommentar hinzugefügt) nachzuvollziehen.
            </li>
          </ol>
        </div>
      </Card>

      <div className="grid gap-4 sm:grid-cols-2">
        <Card title="Workflow History">
          <p className="text-sm text-slate-600">
            Gespeicherte Workflow-Läufe ansehen, Review Status ändern und
            Kommentare hinzufügen.
          </p>
          <Link
            href="/workflows/history"
            className="mt-3 inline-block text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            Zur Workflow History →
          </Link>
        </Card>
        <Card title="CRM Email Drafts">
          <p className="text-sm text-slate-600">
            Gespeicherte Email-Entwürfe prüfen, Review Status setzen und die
            Audit Timeline ansehen.
          </p>
          <Link
            href="/crm"
            className="mt-3 inline-block text-sm font-medium text-brand-600 hover:text-brand-700"
          >
            Zu den CRM Email Drafts →
          </Link>
        </Card>
      </div>
    </div>
    </RequireRole>
  );
}
