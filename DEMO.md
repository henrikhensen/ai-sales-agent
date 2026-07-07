# Demo Runbook

Eine klare, wiederholbare Reihenfolge, um den kompletten AI Sales Agent in
5-10 Minuten vorzuführen — vollständig im Mock/Safe Mode, ohne echte API
Keys, ohne dass irgendeine echte E-Mail versendet wird.

Für die Umgebungsvariablen siehe `.env.example`; für Deployment-Details
siehe [`DEPLOYMENT.md`](./DEPLOYMENT.md). Dieses Dokument beschreibt nur
den Demo-Ablauf in der bereits laufenden lokalen Umgebung.

## 0. Projekt lokal starten

```bash
docker compose up --build -d
```

- Backend: http://localhost:8000 (Swagger unter `/docs`)
- Frontend: http://localhost:3000

Alles läuft im Mock-Modus (`LLM_PROVIDER=mock`,
`EMAIL_INTEGRATION_PROVIDER=mock`, `REPLY_TRACKING_PROVIDER=mock`) — keine
echten API Keys nötig, keine Kosten, keine echte Mailbox wird berührt.

## 1. Login als Admin

1. Im Browser http://localhost:3000/register öffnen.
2. Ein Konto mit Rolle **admin** anlegen (E-Mail/Passwort frei wählbar,
   z. B. `demo-admin@example.com` / `demopassword123`).
3. Danach über http://localhost:3000/login einloggen.

Optional: ein zweites Konto mit Rolle `sales` oder `reviewer` anlegen, um
später die Rollen-Einschränkungen zu zeigen (z. B. dass Audit Logs nur für
`admin` sichtbar sind).

## 2. Sales Workflow testen

1. Navigation → **Workflows → Sales Workflow** (`/workflows/sales`).
2. Formular ausfüllen: Firmenname (z. B. „Demo GmbH“), Produkt/Service
   (z. B. „CRM Software“), optional Empfänger-Name/E-Mail.
3. **Workflow starten** klicken.
4. Ergebnis zeigt: Lead Research, Company Intelligence, Personalization,
   Email Draft — alles Analyse/Entwurf, kein Versand. `human_review_required`
   ist immer `true`.

## 3. Website Research testen

1. Navigation → **Research → Website Research** (`/research/website`).
2. Eine öffentliche URL eingeben (z. B. `https://example.com`).
3. **Analysieren** klicken — zeigt extrahierten Text, keine Mengen-Recherche,
   kein LinkedIn-Scraping, kein Login-Bypass.
4. Alternativ: im Sales-Workflow-Formular „Website Research nutzen“
   aktivieren, um die Integration im Kontext zu zeigen.

## 4. Email Draft ansehen

1. Navigation → **CRM** (`/crm`).
2. Den zuvor erzeugten Email Draft in der Liste öffnen (aufklappen).
3. Zeigt Betreff, Text, Review Status — der Draft ist lokal gespeichert,
   nie versendet.

## 5. Human Review testen

1. Im aufgeklappten Email Draft (CRM-Seite) den **Review Status** auf
   `approved` setzen, optional mit Kommentar.
2. Zeigt: `approved` bedeutet ausschließlich interne Freigabe — es gibt
   keinen Versand-Trigger an dieser Stelle.
3. Die **Review Timeline** darunter zeigt das protokollierte Ereignis.

## 6. Pipeline ansehen

1. Navigation → **CRM Pipeline** (`/crm/pipeline`).
2. Zeigt alle Leads gruppiert nach Pipeline-Status (new, research_completed,
   draft_created, in_review, approved, rejected, archived).
3. Optional: Pipeline-Status eines Leads manuell ändern — rein
   Bookkeeping, kein externer Effekt.

## 7. Do-not-contact Block testen

1. Navigation → **Compliance → Do-not-contact** (`/compliance/do-not-contact`).
2. Neuen Eintrag erstellen: E-Mail des zuvor genutzten Empfängers eintragen,
   Grund angeben (z. B. „Demo Opt-out“).
3. Mit **Check** dieselbe E-Mail prüfen → `is_blocked: true`.
4. Zurück im CRM: den zugehörigen Email Draft erneut auf `approved` setzen
   versuchen → wird mit klarer Meldung blockiert (Do-not-contact hat
   Vorrang vor Review-Freigabe).

## 8. External Draft im Mock-Modus testen

1. Im CRM einen **approved** Email Draft öffnen (nicht durch Do-not-contact
   blockiert).
2. Abschnitt „Externer Draft (Gmail/Outlook)" → **Externen Draft
   erstellen** klicken.
3. Zeigt `provider: mock`, `provider_status: mock_created` — kein echter
   Gmail/Outlook-Zugriff, kein Versand. Es gibt an dieser Stelle keinen
   Send-Button.

## 9. Reply Inbox im Mock-Modus testen

1. Navigation → **Inbox → Replies** (`/replies`).
2. **Recent Replies synchronisieren** klicken.
3. Zeigt simulierte Mock-Antworten mit Kategorie, Sentiment, Confidence
   Score. Eine der Beispielantworten enthält eine Unsubscribe-Formulierung
   — dafür wird automatisch ein Do-not-contact-Hinweis markiert und ggf.
   ein Eintrag vorgeschlagen/erstellt.
4. Es gibt keinen Reply-/Send-Button — nur Lesen, Als-gelesen-markieren,
   Archivieren.

## 10. Compliance Status ansehen

1. Navigation → **Compliance → Compliance Status** (`/compliance/status`).
2. Zeigt auf einen Blick: Do-not-contact aktiv, Human Review aktiv, Email
   Sending **deaktiviert**, Automatic Contact **deaktiviert**, aktive
   Provider (alle `mock`), Rate Limits aktiv, Audit Logs aktiv, sowie die
   Anzahl der zuletzt blockierten Aktionen.

## 11. Audit Logs ansehen

1. Navigation → **Verwaltung → Audit Logs** (`/audit-logs`, nur Admin).
2. Zeigt das Protokoll der bisherigen Demo-Schritte: `login`,
   `sales_workflow_started`/`completed`, `do_not_contact_entry_created`,
   `do_not_contact_check_blocked`, `external_draft_creation_succeeded`,
   `reply_sync_started`/`completed`, ggf. `reply_unsubscribe_signal_detected`.
3. Nach Action/Entity Type/Result filtern, um einzelne Ereignisse zu finden.
4. Keine Secrets, keine vollständigen E-Mail-Inhalte, keine LLM-Prompts in
   den Einträgen — nur Metadaten.

## 12. System Status ansehen

1. Navigation → **System → System Status** (`/system/status`, nur Admin).
2. Zeigt App-Version, Datenbank-/Redis-Status, aktive Provider (alle
   `mock`), Metrics- und Backup-Konfiguration, sowie Production-Warnungen
   (im lokalen Dev-Modus normalerweise leer).

## 13. ICP und Offer Profile erstellen

1. Navigation → **Sales Strategy → ICP Profiles** (`/sales-strategy/icp`).
2. Neues ICP erstellen: Name (z. B. „Mittelstand Logistik"), Zielbranchen
   (z. B. „Logistics"), Zielkeywords, Pain Points, Buying Triggers.
3. Navigation → **Sales Strategy → Offers** (`/sales-strategy/offers`).
4. Neues Offer erstellen: Name, Value Proposition (Pflichtfeld), Key
   Benefits, Call to Action.

## 14. ICP Fit Score und Offer Preview ansehen

1. Auf der ICP-Seite: Abschnitt „ICP Fit Check" — Profil auswählen,
   Company Name/Industry/Website-Text eingeben, **Fit Check ausführen**.
2. Zeigt `fit_score`, `fit_level`, matched/missing/negative Signale sowie
   eine Empfehlung. Bei fehlenden Eingaben erscheinen Warnings statt
   erfundener Werte.
3. Auf der Offer-Seite: Abschnitt „Offer Preview" — Profil auswählen,
   **Preview generieren**.
4. Zeigt Summary, Positionierung, CTA-Vorschlag und Warnings (z. B. fehlende
   Proof Points, aktive `forbidden_claims`).

## 15. Sales Workflow mit ICP und Offer starten

1. Navigation → **Workflows → Sales Workflow** (`/workflows/sales`).
2. Formular wie in Schritt 2 ausfüllen, zusätzlich unter „ICP Profil" und
   „Offer Profil" die zuvor erstellten Profile auswählen (beide optional).
3. **Workflow starten** klicken.
4. Ergebnis zeigt zusätzlich die Abschnitte „ICP Fit" (Fit Score, Fit Level,
   Warnings) und „Offer" (Summary, Warnings) — Email Draft nutzt die
   Value Proposition und Benefits aus dem Offer Profil als Kontext.
5. Zeigt: Do-not-contact-Hinweis „Do-not-contact bleibt aktiv" und Human
   Review-Hinweis „Human Review bleibt aktiv, Approved bedeutet nicht
   Versand" bleiben unverändert sichtbar — kein Send-Button, kein
   automatischer Versand, auch mit ICP/Offer.
6. Workflow History (`/workflows/history`) öffnen: der Lauf zeigt
   `icp_fit_score`/`icp_fit_level` und `offer_summary` im gespeicherten
   Ergebnis.

## Zurück auf Mock stellen

Alles ist bereits Mock — falls zwischendurch ein echter Provider getestet
wurde: `LLM_PROVIDER=mock`, `EMAIL_INTEGRATION_PROVIDER=mock`,
`REPLY_TRACKING_PROVIDER=mock` in `.env` setzen und Backend neu starten.
Mit **Compliance Status** verifizieren: alle `*_real_*_enabled`-Felder
müssen `false` sein.

## Wichtig für die Demo

- Keine echten API Keys nötig — alles läuft mit Platzhaltern aus
  `.env.example`.
- An keiner Stelle wird eine echte E-Mail versendet.
- Jeder externe Schritt (External Draft, Reply Sync) ist ein bewusster,
  einzelner Klick — nie automatisch ausgelöst.
