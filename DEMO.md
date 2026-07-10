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

## 1a. Onboarding und Admin Controls ansehen

1. **Onboarding öffnen** (`/onboarding`) — zeigt den Setup-Fortschritt in
   Prozent, die Setup-Schritte (Welcome, Company Setup, Offer Setup, ICP
   Setup, Safe Mode Review, Provider Settings Review, Compliance Review,
   Do-not-contact Review, First Lead Sourcing, First Qualification, First
   Outreach Queue, First Draft Review, Completion) sowie das Readiness
   Level mit Blockers/Warnings/Recommendations.
2. **Offer Profile prüfen** — noch keins angelegt → Readiness zeigt einen
   Blocker „No active Offer Profile exists yet.“ und Setup Checklist
   markiert „Offer Profile vorhanden“ als `blocker`.
3. **ICP Profile prüfen** — analog, noch kein aktives ICP Profile.
4. **Safe Mode Review zeigen** — Link „Zur Seite“ beim Schritt „Safe Mode
   prüfen“ führt zu `/settings`: LLM/Email Integration laufen im
   Mock-Modus, keine echten API Calls.
5. **Admin Controls öffnen** (`/admin/controls`, nur als admin sichtbar):
   - **Human Review Required zeigen**: Badge „Human Review: Pflicht“ — die
     Checkbox dafür existiert bewusst nicht, da dieser Schalter nie
     deaktivierbar ist.
   - **Do-not-contact Required zeigen**: Badge „Do-not-contact: Pflicht“,
     ebenso strukturell immer aktiv.
   - **Dispatch Mode draft_only zeigen**: Select „Dispatch Mode“ steht auf
     „Draft-only (sicher)“; ein Versuch, auf „Manual Send“ zu wechseln,
     wird von der API mit HTTP 400 abgelehnt, solange
     `OUTREACH_DISPATCH_ENABLE_REAL_SEND` nicht in der Umgebung gesetzt ist.
   - Setup Checklist unten auf derselben Seite zeigt alle 13 Punkte
     (`passed`/`warning`/`blocker`/`not_checked`).
6. **Readiness Level zeigen** — zurück auf `/onboarding`: Readiness Level
   ist `not_ready` (fehlendes Offer/ICP). Nach Anlage von Offer und ICP
   (siehe Schritt 13 unten) wechselt es auf `demo_ready`/`internal_ready`.
7. Danach mit **Schritt 2 (Sales Workflow testen)** unten fortfahren, oder
   direkt zu **Schritt 16 (Lead Sourcing)** springen.

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

## 16. Lead Sourcing Campaign erstellen und Mock Run starten

1. Navigation → **Sales Strategy → Lead Sourcing** (`/lead-sourcing`).
2. Zeigt Provider Status: `provider: mock`, Safe Mode aktiv.
3. Neue Campaign erstellen: Name (z. B. „Logistik Q1"), Zielbranche
   „Logistics", optional das zuvor erstellte ICP Profil auswählen.
4. Campaign in der Liste auswählen, dann **Run starten** klicken.
5. Ergebnis zeigt gefundene Kandidaten mit ICP Fit Score, Fit Level,
   Do-not-contact-Status und Duplicate-Status. Dashboard oben zeigt
   Kandidatenanzahl, Duplikate, Do-not-contact-Blocks und den
   durchschnittlichen ICP Fit Score.
6. Optional: **Dry Run starten** klicken — zeigt dieselben Kandidaten zur
   Vorschau, ohne sie dauerhaft zu speichern.

## 17. Do-not-contact Block und Duplikat-Erkennung im Lead Sourcing zeigen

1. Auf der Do-not-contact-Seite einen Eintrag für „Nordwind Logistik GmbH"
   anlegen (einer der Mock-Kandidaten).
2. Zurück auf der Lead Sourcing Seite erneut **Run starten** — der
   Kandidat „Nordwind Logistik GmbH" zeigt jetzt `do_not_contact_status:
   blocked` und kann nicht approved werden (Approve-Button verschwindet /
   Approve schlägt mit klarer Meldung fehl).
3. Denselben Run erneut starten — bereits zuvor gefundene Kandidaten
   zeigen jetzt `duplicate_status: duplicate`.

## 18. Kandidat approven und CRM/Sales Workflow verbinden

1. Einen nicht blockierten Kandidaten aufklappen und **Approve** klicken.
2. Zeigt: Review Status wechselt auf `approved`, CRM Company/Lead werden
   angezeigt (verlinkt).
3. **CRM öffnen** klicken → Company/Lead sind in der CRM-Liste (`/crm`)
   sichtbar.
4. **Sales Workflow manuell starten** klicken → öffnet den Sales Workflow
   (`/workflows/sales`); die Firmendaten müssen manuell eingetragen
   werden — kein automatischer Start, keine automatische Kontaktaufnahme.

## 19. Lead Qualification Run starten und Priority Leads ansehen

1. Navigation → **Sales Strategy → Lead Qualification** (`/lead-qualification`).
2. Zeigt Status: regelbasiert (kein LLM), Safe Mode.
3. Unter „Qualification Run starten" Source „Lead Candidates" wählen,
   Feld für IDs leer lassen (bewertet automatisch alle offenen
   Kandidaten), optional das zuvor erstellte ICP Profil auswählen, dann
   **Run starten** klicken.
4. Ergebnis zeigt Score, Level, Status und `recommended_next_action` je
   Kandidat; Dashboard oben zeigt Qualified/Priority/Needs Review/
   Disqualified/Blocked-Zahlen und den Durchschnitts-Score.
5. Ein Ergebnis mit hohem Score (`priority`) aufklappen — zeigt
   Score-Breakdown, positive Signale und „Sales Workflow manuell
   starten"-Link.

## 20. blocked / duplicate / disqualified Beispiele zeigen

1. Denselben Run erneut starten — bereits zuvor bewertete Kandidaten
   erscheinen mit niedrigerem oder gleichem Score erneut (Duplicate
   Status wurde bereits in Lead Sourcing gesetzt und wird hier
   berücksichtigt).
2. Für den Kandidaten mit Do-not-contact-Eintrag (siehe Schritt 17):
   Qualification Run zeigt `qualification_status: blocked` und
   `recommended_next_action: blocked_do_not_contact` — unabhängig vom
   Score.
3. Ein Ergebnis mit sehr niedrigem Score zeigt `disqualified` mit
   Begründung im `disqualification_reason`.

## 21. Recommended Outreach Angle ansehen und Lead manuell übernehmen

1. Ein `qualified`- oder `priority`-Ergebnis aufklappen und den
   `recommended_outreach_angle` sowie die Score-Breakdown-Details lesen.
2. **Sales Workflow manuell starten** klicken.
3. Auf der Sales-Workflow-Seite im Feld „Qualification Result ID" die ID
   des Ergebnisses eintragen und **Kontext laden** klicken — zeigt Score,
   Level, Status, positive/negative Signale und ggf. eine Warnung bei
   schwachem Fit direkt im Workflow-Formular, rein informativ.
4. Formular danach wie gewohnt manuell ausfüllen und **Workflow
   starten** — kein automatischer Versand, Human Review bleibt
   erforderlich.

## 22. Outreach Campaign Queue: Queue bauen, vorbereiten und Batch zeigen

1. Auf der Lead-Qualification-Seite bei einem `priority`-Ergebnis auf
   **„Zur Outreach Queue hinzufügen"** klicken — führt zu **Sales
   Strategy → Outreach Queue** (`/outreach`) mit vorausgefüllter
   Qualification-Result-ID.
2. Unter „Neue Campaign erstellen" eine Campaign anlegen (z. B. „Q3
   Logistics Push"), optional ICP/Offer-Profil zuweisen.
3. Campaign in der Liste auswählen, dann unter „Queue bauen" zunächst
   **Dry Run** aktivieren und bauen — zeigt eine Vorschau ohne
   dauerhafte Queue Items (`dry_run: true`, keine IDs).
4. Dry Run deaktivieren und erneut bauen — Queue Items erscheinen unten
   mit Score, Level, `queue_status`, Recommended Outreach Angle.
5. Für den zuvor unter Schritt 17 mit Do-not-contact blockierten
   Kandidaten: das entsprechende Queue Item zeigt `queue_status:
   blocked` und kann nicht für den Workflow vorbereitet werden — Fehler
   `409` bei einem Versuch macht das sichtbar.
6. Ein `queued`-Item mit **„Für Workflow vorbereiten"** vorbereiten —
   startet einen internen Sales-Workflow-Lauf (Mock LLM) und legt einen
   internen Email Draft an; Queue Status wechselt auf
   `workflow_prepared`/`review_pending`.
7. Draft/Review über den Link „Draft/Review öffnen" auf der bestehenden
   Reviews-Seite ansehen — Human Review bleibt Pflicht, `approved`
   bedeutet weiterhin nicht Versand.
8. Unter „Batch Preparation" (Mock/Safe Mode) mehrere offene Queue Items
   auf einmal vorbereiten lassen — Ergebnis zeigt Prepared/Skipped/
   Blocked/Failed Counts. Es wurde an keiner Stelle eine E-Mail
   gesendet oder ein externer Draft automatisch erstellt.

## 23. Controlled Outreach Dispatch: Readiness, Compliance Ack und Draft im Mock Mode

1. Auf der Outreach-Queue-Seite (`/outreach`) ein Queue Item mit Status
   `approved` (aus Schritt 22) suchen — dort erscheint der Abschnitt
   „Controlled Dispatch".
2. **„Readiness prüfen"** klicken — zeigt `is_ready` sowie alle acht
   Checks (Do-not-contact, Human Review, Email Draft, Queue Item,
   Rate Limit, Provider Config, Recipient, Compliance Ack).
3. Blocker zeigen, falls vorhanden: für den unter Schritt 17 blockierten
   Kandidaten schlägt der Do-not-contact-Check fehl und die Aktion bleibt
   verweigert — der Provider wird dabei nie aufgerufen.
4. **„Externen Draft vorbereiten"** klicken — erstellt einen
   `OutreachDispatch`-Datensatz und öffnet das Bestätigungs-Modal.
5. Im Modal die fünf Compliance-Statements bestätigen (Kontakt-Erlaubnis,
   Do-not-contact geprüft, Human Review abgeschlossen, Draft/kontrollierter
   Versand, rechtliche Verantwortung) und **„Compliance bestätigen"**
   klicken.
6. Die Checkbox „Ich bestätige diese kontrollierte Aktion" aktivieren und
   **„Externen Draft erstellen"** klicken (Final Confirmation) — im
   Default-Modus (`draft_only`) erscheint kein Send-Button, nur dieser
   Draft-Button.
7. Ergebnis zeigt `dispatch_status: external_draft_created` mit
   Mock-Provider-URL; das Queue Item wechselt ebenfalls auf
   `external_draft_created`.
8. **Outreach Dispatch Dashboard** (`/outreach/dispatch`) ansehen — zeigt
   Mode (Draft-only), Provider (Mock), Real Send (deaktiviert) sowie
   Zähler nach Status.
9. **Audit Logs** (`/audit-logs`) ansehen — Einträge wie
   `outreach_dispatch_created`, `outreach_compliance_ack_set`,
   `outreach_external_draft_created_from_dispatch` sind sichtbar, ohne
   Secrets oder vollständige Email Bodies.
10. Erklären: An keiner Stelle wurde eine E-Mail gesendet — es wurde
    ausschließlich ein Draft beim (Mock-)Provider simuliert.

## 24. Legal/Compliance Pack und Data Retention

1. **Compliance Documents öffnen** (`/compliance/documents`) — zeigt
   Privacy Notice Template, Data Processing Summary, Subprocessors
   Summary, Data Retention Summary, User Responsibility Notice, Outreach
   Safety Notice, Provider Data Transfer Notice, Legal Review Required
   Notice.
2. **Legal Review Hinweis zeigen** — der rot hinterlegte Disclaimer oben
   auf der Seite: keine Rechtsberatung, keine Zertifizierung, echte
   Nutzung braucht eine eigene rechtliche Prüfung.
3. **Data Retention Policies zeigen** (`/compliance/data-retention`) —
   noch keine Policy angelegt; eine neue Policy anlegen (z. B. „Old
   Replies", entity_type `reply`, 180 Tage, Aktion `anonymize`).
4. **Dry Run starten** — zeigt `total_scanned`/`total_eligible` an,
   `total_processed` bleibt `0`. Betonen: Dry Run verändert nie Daten.
5. **Data Request erstellen** (`/compliance/data-requests`) — z. B.
   Request Type `export`, Subject Email `demo@example.com`.
6. **Data Export ausführen** — entweder über den Request („Export
   ausführen") oder direkt im Export-Suchformular auf derselben Seite.
7. **Zeigen, dass keine Secrets enthalten sind** — im JSON-Preview des
   Exports ist weder ein API Key noch ein Token noch ein Passwort
   enthalten.
8. **Customer Readiness zeigen** — `CUSTOMER_READINESS.md` mit den neuen
   Abschnitten „Legal/Compliance Pack Checklist", „Data Retention
   Checklist", „Data Export Checklist", „Data Subject Request Checklist".
9. **Safety Gate zeigen** — `/onboarding` → Readiness-Karte: die Checks
   `compliance_documents_available`, `data_export_available`,
   `data_subject_request_flow_available` sind `true`;
   `legal_review_required_acknowledged` ist immer `true` (nie
   abschaltbar).
10. Erklären: Kein automatischer Versand, keine automatische
    Löschung/Anonymisierung ohne explizite Bestätigung, aktive
    Do-not-contact-Einträge werden nie angefasst, Audit Logs werden nie
    gelöscht (Append-only).

## 25. Beta Feedback Loop und Quality Scoring

1. **Quality Dashboard öffnen** (`/quality`) — zeigt Konfiguration
   (Scoring/Feedback aktiv, regelbasiert), Beta Readiness, Durchschnitts-
   Scores, Top Issues/Verbesserungsvorschläge. Direkt nach dem Start meist
   `not_ready`/wenig Daten — normal, da noch nichts bewertet wurde.
2. **Sales Workflow erneut laufen lassen** (`/workflows/sales`, siehe
   Abschnitt 2/15) — nach Abschluss zeigt die Workflow-Detail-Seite
   (`/workflows/history/<id>`) automatisch einen Quality-Score-Badge für
   Workflow Run und Email Draft.
3. **Quality Dashboard erneut öffnen** — jetzt mit einem Score befüllt;
   zeigen, dass ein niedriger Score nur eine Warnung ist, kein Blocker.
4. **Feedback geben** (`/quality/feedback`) — Entity Type `email_draft`,
   die Email Draft ID von Schritt 2, Bewertung, Kommentar, optional
   „blockierend" ankreuzen. Zeigen: Feedback ändert nie automatisch etwas.
5. **Als Admin/Reviewer Feedback reviewen** — auf derselben Seite
   „Akzeptieren“/„Ablehnen“/„Archivieren“ zeigen.
6. **Blockierendes Feedback und Dispatch Readiness zeigen** — mit
   „blockierend" markiertes, offenes Feedback auf ein Outreach Queue Item
   erzeugen, dann Dispatch Readiness prüfen (`/outreach/dispatch`): der
   Blocker „Open blocking feedback exists…“ erscheint in der Blocker-Liste.
7. **Beta Test Session anlegen** (`/beta-test`) — Session erstellen,
   starten, wieder abschließen; zeigen, dass Workflows getestet/Drafts
   geprüft/Feedback/Blocker/Bugs automatisch zusammengefasst werden.
8. **Beta Dashboard (nur Admin) zeigen** — Sessions-Übersicht,
   `readiness_level`, Empfehlungen.
9. **Safety Gate zeigen** — `/onboarding` → Readiness-Karte: die neuen
   Checks `beta_feedback_loop_available`, `blocking_feedback_respected`
   und `quality_beta_readiness_level`.
10. Erklären: Quality Scores sind Entscheidungshilfen, keine Garantien;
    Feedback löst nie einen Versand oder automatischen Redraft aus; „Beta
    Ready" ist ein technisches Signal, keine rechtliche Freigabe; Human
    Review und Do-not-contact bleiben in jedem Fall verpflichtend.

## Zurück auf Mock stellen

Alles ist bereits Mock — falls zwischendurch ein echter Provider getestet
wurde: `LLM_PROVIDER=mock`, `EMAIL_INTEGRATION_PROVIDER=mock`,
`REPLY_TRACKING_PROVIDER=mock`, `LEAD_SOURCING_PROVIDER=mock`,
`LEAD_QUALIFICATION_USE_LLM=false`, `OUTREACH_DISPATCH_MODE=draft_only`,
`OUTREACH_DISPATCH_ENABLE_REAL_SEND=false` in `.env` setzen und Backend
neu starten. Mit **Compliance Status** verifizieren:
alle `*_real_*_enabled`-Felder müssen `false` sein.

## Wichtig für die Demo

- Keine echten API Keys nötig — alles läuft mit Platzhaltern aus
  `.env.example`.
- An keiner Stelle wird eine echte E-Mail versendet.
- Jeder externe Schritt (External Draft, Reply Sync) ist ein bewusster,
  einzelner Klick — nie automatisch ausgelöst.
