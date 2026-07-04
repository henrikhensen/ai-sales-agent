# AI Sales Agent — Backend

Backend-Grundgerüst für ein **AI Sales Agent SaaS System**.

Diese Phase liefert ausschließlich das **Setup und die Basisstruktur** — kein
Business-Logic-Code. Das System ist vollständig lauffähig: FastAPI-App,
async PostgreSQL-Anbindung, Redis-Anbindung, Health-Check-Endpoint und ein
komplettes Docker-Setup.

---

## Tech Stack

| Komponente     | Technologie          |
| -------------- | -------------------- |
| Sprache        | Python 3.12          |
| Web Framework  | FastAPI              |
| Datenbank      | PostgreSQL (asyncpg) |
| Cache / Broker | Redis                |
| Validierung    | Pydantic v2          |
| ORM            | SQLAlchemy 2 (async) |
| Container      | Docker + Compose     |

---

## Architektur

Das Projekt folgt der **Clean Architecture** mit strikter Schichtentrennung.
Abhängigkeiten zeigen immer nach innen (Richtung `domain`).

```
┌──────────────────────────────────────────────┐
│  api            HTTP-Schicht (FastAPI Router)  │
├──────────────────────────────────────────────┤
│  application    Use Cases / Orchestrierung     │
├──────────────────────────────────────────────┤
│  domain         Entities & Geschäftsregeln     │
├──────────────────────────────────────────────┤
│  infrastructure DB, Redis, Repositories        │
├──────────────────────────────────────────────┤
│  shared         Konfiguration & Querschnitt    │
└──────────────────────────────────────────────┘
```

- **domain** — reine Geschäftsobjekte, keine Framework-Abhängigkeiten (leer in dieser Phase).
- **application** — Use Cases, koordiniert Domain + Infrastruktur (leer in dieser Phase).
- **infrastructure** — technische Umsetzung: DB-Session, Redis-Client, Base-Repository.
- **api** — FastAPI-Router, Request/Response-Schemas, Endpoints.
- **shared** — Konfiguration (`Settings`) und geteilte Hilfsmittel.

---

## Projektstruktur

```
AI-Sales-Agent/
├── backend/
│   ├── api/
│   │   └── v1/
│   │       ├── routes/
│   │       │   └── health.py        # /health Endpoint
│   │       ├── router.py            # v1 Router-Aggregation
│   │       └── schemas.py           # Pydantic Response-Modelle
│   ├── application/                 # Use Cases (Phase folgt)
│   ├── domain/                      # Entities (Phase folgt)
│   ├── infrastructure/
│   │   ├── database/
│   │   │   ├── base.py              # SQLAlchemy DeclarativeBase
│   │   │   └── session.py           # Async Engine + Session
│   │   ├── redis/
│   │   │   └── client.py            # Async Redis Client
│   │   └── repositories/
│   │       └── base.py              # Abstraktes Base-Repository
│   ├── shared/
│   │   └── config.py               # Pydantic Settings
│   └── main.py                     # FastAPI Entry Point
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup

### Voraussetzungen

- Docker & Docker Compose
- (optional für lokalen Betrieb ohne Docker) Python 3.12

### 1. Environment-Datei anlegen

```bash
cp .env.example .env
```

### 2. Mit Docker starten (empfohlen)

```bash
docker compose up --build
```

Das startet drei Services:

- `backend` — FastAPI auf Port **8000**
- `postgres` — PostgreSQL auf Port **5432**
- `redis` — Redis auf Port **6379**

Die App wartet dank Healthchecks, bis PostgreSQL und Redis bereit sind.

### 3. Lokal ohne Docker starten (optional)

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt

# POSTGRES_HOST und REDIS_HOST in .env auf "localhost" setzen
uvicorn backend.main:app --reload
```

---

## Endpoints

| Methode | Pfad                          | Beschreibung                                |
| ------- | ----------------------------- | ------------------------------------------- |
| GET     | `/`                           | Service-Metadaten                           |
| GET     | `/api/v1/health`              | Health-Check inkl. DB- und Redis-Status     |
| POST    | `/api/v1/agents/demo`         | Demo-Agent (verifiziert das Agent-Framework)|
| POST    | `/api/v1/agents/lead-research`| Lead Research Agent (Unternehmensanalyse)   |
| POST    | `/api/v1/agents/company-intelligence` | Company Intelligence Agent (tiefere Strategieanalyse) |
| POST    | `/api/v1/agents/personalization` | Personalization Engine (Personalisierungsstrategie) |
| POST    | `/api/v1/agents/email-draft`  | Email Draft Agent (E-Mail-Entwurf, kein Versand) |
| GET     | `/docs`                       | Interaktive OpenAPI-Dokumentation (Swagger) |

### Beispiel Health-Check

```bash
curl http://localhost:8000/api/v1/health
```

```json
{
  "status": "ok",
  "service": "AI Sales Agent",
  "environment": "development",
  "components": {
    "database": { "status": "up" },
    "redis": { "status": "up" }
  }
}
```

---

## Lead Research Agent

Der **Lead Research Agent** analysiert ein einzelnes Unternehmen anhand der
vom Nutzer bereitgestellten Informationen und erstellt daraus ein
strukturiertes Lead-Profil. Er nutzt das AI-Agent-Framework und den
konfigurierten LLM-Provider (standardmäßig den `mock`-Provider, damit das
System ohne API-Keys lauffähig ist).

### Was der Agent macht

- Nimmt Unternehmensangaben entgegen (Name, optional Website, Branche, Ort, Notizen).
- Erstellt eine sachliche Kurzbeschreibung ausschließlich aus dem Input.
- Leitet plausible Zielkunden, Pain Points und analytische Sales-Angles ab.
- Markiert fehlende Informationen offen in `missing_information`.
- Nennt die Analysegrundlage in `sources_used`.
- Vergibt einen `confidence_score` zwischen `0.0` und `1.0` — je weniger belastbar
  die Eingaben, desto niedriger der Wert.

### Was der Agent ausdrücklich **nicht** macht

- **Keine automatische Kontaktaufnahme.** Es werden keine E-Mails, Nachrichten
  oder Anrufe erzeugt, versendet oder geplant.
- **Keine Massenakquise, kein Spam, keine LinkedIn-Automation.**
- **Keine erfundenen Fakten** — keine erfundenen Ansprechpartner, Umsätze,
  Mitarbeiterzahlen oder Kundenlisten.
- **Keine privaten oder unrechtmäßig beschafften Daten.** Es werden ausschließlich
  die vom Nutzer bereitgestellten Informationen verwendet; es findet kein
  externer Datenabruf statt.
- Die Identitätsfelder (`company_name`, `website_url`, `industry`, `location`)
  im Ergebnis stammen immer aus dem Input, nicht vom Modell.

> **Hinweis:** Der Agent liefert ausschließlich eine Analyse. Jede tatsächliche
> Kontaktaufnahme bleibt ein separater, **menschlich freizugebender** Schritt.

### Beispiel-Request

```bash
curl -X POST http://localhost:8000/api/v1/agents/lead-research \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme GmbH",
    "website_url": "https://acme.example.com",
    "industry": "Logistics",
    "location": "Berlin",
    "notes": "Auf einer Fachmesse kennengelernt."
  }'
```

Validierung: `company_name` ist Pflicht, leere Strings werden abgelehnt (`422`),
und `website_url` muss — falls angegeben — eine gültige `http(s)`-URL sein.

### Beispiel-Response

```json
{
  "company_name": "Acme GmbH",
  "website_url": "https://acme.example.com/",
  "industry": "Logistics",
  "location": "Berlin",
  "short_summary": "Logistikunternehmen mit Sitz in Berlin (auf Basis der Nutzerangaben).",
  "target_customers": ["Mittelständische Versandhändler", "Produzierende Betriebe"],
  "likely_pain_points": ["Lieferketten-Transparenz", "Kostendruck bei der Last-Mile"],
  "possible_sales_angles": ["Effizienzsteigerung in der Disposition"],
  "confidence_score": 0.4,
  "missing_information": ["Mitarbeiterzahl", "Ansprechpartner", "Umsatz"],
  "sources_used": ["Vom Nutzer bereitgestellter Firmenname", "Vom Nutzer bereitgestellte Notizen"]
}
```

> Mit dem Standard-`mock`-Provider ist die Antwort deterministisch und dient
> nur der Verifikation der Pipeline. Für echte Analysen `LLM_PROVIDER=anthropic`
> setzen.

---

## Company Intelligence Agent

Der **Company Intelligence Agent** erstellt aus den bereitgestellten
Unternehmensinformationen eine **tiefere, strategische Unternehmensanalyse**.
Er nutzt dasselbe AI-Agent-Framework und den konfigurierten LLM-Provider
(standardmäßig `mock`).

### Unterschied zum Lead Research Agent

| | Lead Research Agent | Company Intelligence Agent |
| --- | --- | --- |
| Fokus | Schnelle erste Qualifizierung eines Leads | Tiefe strategische Analyse |
| Input | Name, Website, Branche, Ort, Notizen | Zusätzlich Beschreibung, Website-Text, bekannte Produkte & Kunden |
| Output | Kurzprofil (Zielkunden, Pain Points, Sales-Angles) | Umfassendes Profil (Business-Summary, Positionierung, Buyer Personas, Value Proposition, Wettbewerbskontext, Sales-Relevanz, Personalisierungs-Hooks) |
| Einsatz | Erster Blick auf einen Lead | Vorbereitung eines fundierten, individuellen Vertriebsansatzes |

### Was der Agent macht

- Erstellt eine strategische Business-Summary ausschließlich aus dem Input.
- Leitet Produkte/Services, Zielsegmente, Buyer Personas, Value Proposition und
  Positionierung ab.
- Nennt möglichen Wettbewerbskontext **nur**, wenn Wettbewerber im Input genannt
  wurden oder klar aus dem bereitgestellten Text hervorgehen.
- Liefert `sales_relevance`, `potential_business_challenges` und
  `personalization_hooks` (letztere ohne erfundene Fakten).
- Markiert fehlende Informationen in `missing_information` und die Grundlage in
  `sources_used`; `confidence_score` (0.0–1.0) sinkt bei geringer Datenlage.

### Was der Agent ausdrücklich **nicht** macht

- **Keine automatische Kontaktaufnahme.** Keine E-Mails, Nachrichten oder Anrufe.
- **Keine Massenakquise, kein Spam, keine LinkedIn-Automation.**
- **Keine erfundenen Fakten** — keine Ansprechpartner, Umsätze, Mitarbeiterzahlen,
  Kundenreferenzen oder Wettbewerber.
- **Keine privaten oder unrechtmäßig beschafften Daten.** Nur Nutzer-Input; kein
  externer Datenabruf.
- Identitätsfelder (`company_name`, `website_url`, `industry`, `location`) im
  Ergebnis stammen immer aus dem Input, nicht vom Modell.

> **Hinweis:** Der Agent liefert ausschließlich eine Analyse. Jede tatsächliche
> Kontaktaufnahme bleibt ein separater, **menschlich freizugebender** Schritt.

### Beispiel-Request

```bash
curl -X POST http://localhost:8000/api/v1/agents/company-intelligence \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "HubSpot",
    "website_url": "https://www.hubspot.com",
    "industry": "CRM Software",
    "location": "USA",
    "company_description": "B2B SaaS für Marketing, Sales und Service.",
    "known_products": ["Marketing Hub", "Sales Hub"],
    "known_customers": ["KMU"]
  }'
```

Validierung: `company_name` ist Pflicht, leere Strings werden abgelehnt (`422`),
`website_url` muss — falls angegeben — eine gültige `http(s)`-URL sein, und
Listen dürfen keine leeren Strings enthalten.

### Beispiel-Response

```json
{
  "company_name": "HubSpot",
  "website_url": "https://www.hubspot.com/",
  "industry": "CRM Software",
  "location": "USA",
  "business_summary": "B2B-SaaS-Anbieter für Marketing, Sales und Service (auf Basis der Nutzerangaben).",
  "products_and_services": ["Marketing Hub", "Sales Hub"],
  "target_segments": ["Kleine und mittlere Unternehmen"],
  "likely_buyer_personas": ["Marketing-Leitung", "Vertriebsleitung"],
  "value_proposition": ["All-in-one-Plattform für Kundengewinnung und -bindung"],
  "positioning_summary": "Positioniert als integrierte CRM-Suite für den Mittelstand.",
  "possible_competitive_context": [],
  "sales_relevance": ["Wachsender Bedarf an konsolidierten CRM-Lösungen"],
  "potential_business_challenges": ["Integration bestehender Toollandschaften"],
  "personalization_hooks": ["Fokus auf Marketing- und Sales-Automatisierung"],
  "missing_information": ["Mitarbeiterzahl", "Ansprechpartner", "Umsatz"],
  "sources_used": ["Vom Nutzer bereitgestellte Unternehmensbeschreibung", "Vom Nutzer bereitgestellte Produktliste"],
  "confidence_score": 0.45
}
```

> **Mock-Modus:** Mit dem Standard-`mock`-Provider wird **keine echte
> KI-Analyse** erzeugt — die Antwort ist deterministisch und dient nur der
> Verifikation der Pipeline (Identitätsfelder gespiegelt, analytische Felder
> leer, `confidence_score` = `1.0`). Für echte Analysen `LLM_PROVIDER=anthropic`
> setzen (verursacht API-Kosten).

---

## Personalization Engine

Die **Personalization Engine** erstellt aus Unternehmens-, Lead- und
Analyseinformationen (z. B. den Ergebnissen des Lead Research Agent oder des
Company Intelligence Agent) eine **strukturierte Personalisierungsstrategie**
für einen menschlichen Sales-Mitarbeiter. Sie nutzt dasselbe AI-Agent-Framework
und den konfigurierten LLM-Provider (standardmäßig `mock`).

### Unterschied zum Lead Research Agent und Company Intelligence Agent

| | Lead Research Agent | Company Intelligence Agent | Personalization Engine |
| --- | --- | --- | --- |
| Fokus | Schnelle erste Qualifizierung eines Leads | Tiefe strategische Analyse | Personalisierte Ansprache-Strategie |
| Input | Name, Website, Branche, Ort, Notizen | Zusätzlich Beschreibung, Website-Text, Produkte & Kunden | Zusätzlich Lead-/Company-Intelligence-Summaries, Angebot, Value Proposition, Pain Points, Trigger |
| Output | Kurzprofil (Zielkunden, Pain Points, Sales-Angles) | Umfassendes Profil (Business-Summary, Buyer Personas, Positionierung, ...) | Personalisierungsstrategie (Gesprächseinstiege, Pain-Point-Angles, CTAs, Einwand-Risiken, ...) |
| Einsatz | Erster Blick auf einen Lead | Vorbereitung eines fundierten Vertriebsansatzes | Vorbereitung des individuellen Erstkontakts durch einen Menschen |

### Was der Agent macht

- Fasst zusammen, wie ein Vertriebsansatz auf Basis der gelieferten Informationen
  personalisiert werden könnte (`personalization_summary`).
- Leitet Beobachtungen, Gesprächseinstiege, Pain-Point-Angles, Werteargumente,
  Glaubwürdigkeitspunkte und mögliche Einwände ab — ausschließlich aus dem Input.
- Schlägt CTA-**Ideen** vor (`suggested_ctas`), niemals eine fertige Nachricht.
- Nennt Aussagen, die **nicht** verwendet werden dürfen, weil sie nicht belegt
  sind (`do_not_use_claims`).
- Markiert fehlende Informationen in `missing_information` und die Grundlage in
  `sources_used`; `confidence_score` (0.0–1.0) sinkt bei geringer Datenlage.

### Was der Agent ausdrücklich **nicht** macht

- **Schreibt keine E-Mails.** Es wird keine fertige Outreach-Nachricht erzeugt.
- **Versendet nichts.** Keine automatische Kontaktaufnahme, keine Anrufe.
- **Keine Massenakquise, kein Spam, keine LinkedIn-Automation.**
- **Keine erfundenen Fakten** — keine erfundenen Ansprechpartner, Umsätze,
  Mitarbeiterzahlen oder Kundenreferenzen.
- **Keine privaten oder unrechtmäßig beschafften Daten.** Nur Nutzer-Input oder
  ausdrücklich bereitgestellte Quellen (z. B. Summaries anderer Agenten); kein
  externer Datenabruf.
- Identitätsfelder (`company_name`, `website_url`, `industry`) im Ergebnis
  stammen immer aus dem Input, nicht vom Modell.

> **Hinweis:** Der Agent liefert ausschließlich eine Personalisierungs**strategie**.
> Jede tatsächliche Kontaktaufnahme bleibt ein separater, **menschlich
> freizugebender** Schritt.

### Beispiel-Request

```bash
curl -X POST http://localhost:8000/api/v1/agents/personalization \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme GmbH",
    "website_url": "https://acme.example.com",
    "industry": "Logistics",
    "location": "Berlin",
    "lead_summary": "Logistikunternehmen mit Sitz in Berlin.",
    "company_intelligence_summary": "Mittelständischer Frachtdienstleister.",
    "target_persona": "Leiter Operations",
    "product_or_service_offered": "Sendungs-Sichtbarkeitsplattform",
    "value_proposition": "Echtzeit-Tracking von Sendungen.",
    "known_pain_points": ["Mangelnde Sendungstransparenz"],
    "known_triggers": ["Kürzliche Expansion in neue Märkte"],
    "notes": "Auf einer Fachmesse kennengelernt."
  }'
```

Validierung: `company_name` und `product_or_service_offered` sind Pflicht, leere
Strings werden abgelehnt (`422`), `website_url` muss — falls angegeben — eine
gültige `http(s)`-URL sein, und Listen dürfen keine leeren Strings enthalten.

### Beispiel-Response

```json
{
  "company_name": "Acme GmbH",
  "website_url": "https://acme.example.com/",
  "industry": "Logistics",
  "personalization_summary": "Fokus auf operative Effizienzgewinne durch Sendungstransparenz.",
  "relevant_observations": ["Kürzliche Expansion in neue Märkte erhöht Bedarf an Transparenz"],
  "possible_conversation_starters": ["Anknüpfen an die genannte Marktexpansion"],
  "pain_point_angles": ["Mangelnde Sendungstransparenz als Kernproblem adressieren"],
  "value_arguments": ["Echtzeit-Tracking reduziert manuelle Nachfragen"],
  "credibility_points": [],
  "objection_risks": ["Wechselaufwand von bestehenden Tools"],
  "suggested_ctas": ["Kurzes 15-minütiges Discovery-Gespräch vorschlagen"],
  "do_not_use_claims": ["Konkrete Kosteneinsparung in Prozent (nicht belegt)"],
  "missing_information": ["Ansprechpartner", "Aktuelle Tool-Landschaft"],
  "sources_used": ["Vom Nutzer bereitgestellte Lead-Zusammenfassung", "Vom Nutzer bereitgestellte Company-Intelligence-Zusammenfassung"],
  "confidence_score": 0.5
}
```

> **Mock-Modus:** Mit dem Standard-`mock`-Provider wird **keine echte
> KI-Personalisierung** erzeugt — die Antwort ist deterministisch und dient nur
> der Verifikation der Pipeline (Identitätsfelder gespiegelt, strategische
> Felder leer, `confidence_score` = `1.0`). Für echte Personalisierung
> `LLM_PROVIDER=anthropic` setzen (verursacht API-Kosten).

---

## Email Draft Agent

Der **Email Draft Agent** erstellt aus Unternehmens-, Lead- und
Personalisierungsinformationen (z. B. den Ergebnissen der Personalization
Engine) einen **hochwertigen E-Mail-Entwurf**. Er nutzt dasselbe
AI-Agent-Framework und den konfigurierten LLM-Provider (standardmäßig `mock`).

### Was der Agent macht

- Erstellt genau **einen E-Mail-Entwurf** (`email_body`) mit drei Varianten für
  Betreffzeilen (`subject_lines`), Eröffnungssätze (`alternative_openings`) und
  Call-to-Actions (`alternative_ctas`).
- Nennt, welche Personalisierungs-Inputs im Entwurf verwendet wurden
  (`personalization_used`).
- Markiert Aussagen, die vor dem Versand geprüft werden müssen
  (`claims_to_verify`), sowie Bedingungen, unter denen der Entwurf **nicht**
  verwendet werden sollte (`do_not_send_if`).
- Erklärt in `compliance_notes`, warum eine menschliche Prüfung nötig ist.
- Markiert fehlende Informationen in `missing_information`;
  `confidence_score` (0.0–1.0) sinkt bei geringer Datenlage.
- Schreibt kurz, klar und professionell, im gewünschten Ton (`tone`:
  `professional`, `friendly`, `concise`, `consultative`) und in der
  gewünschten Sprache (`language`, Standard: `German`).

### Was der Agent ausdrücklich **nicht** macht

- **Sendet KEINE E-Mails.** Es wird ausschließlich ein Entwurf erzeugt.
- **Keine automatische Kontaktaufnahme, keine Spam-Kampagnen, keine
  LinkedIn-Automation.**
- **Keine erfundenen Fakten** — keine erfundenen Ansprechpartner, Umsätze,
  Mitarbeiterzahlen oder Kundenreferenzen.
- **Keine manipulative oder aggressive Verkaufssprache, keine falsche
  Vertrautheit, keine falsche Dringlichkeit, keine Täuschung.**
- **Keine privaten oder unrechtmäßig beschafften Daten.** Nur Nutzer-Input oder
  ausdrücklich bereitgestellte Quellen; kein externer Datenabruf.
- Der Firmenname (`company_name`) im Ergebnis stammt immer aus dem Input, nicht
  vom Modell.

> **Hinweis:** Jeder Entwurf **muss von einem Menschen geprüft und freigegeben
> werden**, bevor er verwendet wird. Der tatsächliche Versand bleibt ein
> separater, **menschlich freizugebender** Schritt außerhalb dieses Agenten —
> dieser Agent versendet selbst niemals eine E-Mail.

### Beispiel-Request

```bash
curl -X POST http://localhost:8000/api/v1/agents/email-draft \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme GmbH",
    "website_url": "https://acme.example.com",
    "industry": "Logistics",
    "recipient_role": "Leiter Operations",
    "recipient_name": "Jane Doe",
    "sender_name": "John Smith",
    "sender_company": "Beta Vertrieb GmbH",
    "product_or_service_offered": "Sendungs-Sichtbarkeitsplattform",
    "personalization_summary": "Fokus auf operative Effizienzgewinne.",
    "relevant_observations": ["Kürzliche Expansion in neue Märkte"],
    "pain_point_angles": ["Mangelnde Sendungstransparenz"],
    "value_arguments": ["Echtzeit-Tracking reduziert manuelle Nachfragen"],
    "credibility_points": ["Arbeitet mit mittelständischen Frachtdienstleistern"],
    "suggested_ctas": ["Kurzes 15-minütiges Discovery-Gespräch vorschlagen"],
    "tone": "consultative",
    "language": "German",
    "notes": "Auf einer Fachmesse kennengelernt."
  }'
```

Validierung: `company_name` und `product_or_service_offered` sind Pflicht,
leere Strings werden abgelehnt (`422`), `website_url` muss — falls angegeben —
eine gültige `http(s)`-URL sein, `tone` muss — falls angegeben — einer von
`professional`, `friendly`, `concise`, `consultative` sein, und Listen dürfen
keine leeren Strings enthalten.

### Beispiel-Response

```json
{
  "company_name": "Acme GmbH",
  "subject_lines": [
    "Mehr Transparenz in Ihrer Sendungslogistik",
    "Kurze Frage zu Ihrer Sendungsverfolgung",
    "Effizienzgewinne bei der Sendungstransparenz"
  ],
  "email_body": "Hallo Frau Doe,\n\nIch habe gesehen, dass Acme GmbH kürzlich in neue Märkte expandiert ist. Dabei wird die Sendungstransparenz oft zur Herausforderung...\n\nViele Grüße\nJohn Smith",
  "alternative_openings": [
    "Ich habe gesehen, dass Acme GmbH kürzlich expandiert ist...",
    "Als Leiter Operations bei Acme GmbH kennen Sie vermutlich die Herausforderung...",
    "Kurze Frage zu Ihrer aktuellen Sendungsverfolgung..."
  ],
  "alternative_ctas": [
    "Passt ein kurzes 15-minütiges Gespräch diese Woche?",
    "Darf ich Ihnen zwei Terminvorschläge schicken?",
    "Wäre ein kurzer Austausch für Sie interessant?"
  ],
  "personalization_used": ["Kürzliche Expansion in neue Märkte", "Mangelnde Sendungstransparenz"],
  "claims_to_verify": ["Genaue Auswirkung der Expansion auf die Logistik nicht bestätigt"],
  "do_not_send_if": ["Ansprechpartner-Name nicht verifiziert", "Firma hat kürzlich abgesagt"],
  "compliance_notes": ["Entwurf muss vor Versand von einem Menschen geprüft werden; Fakten sind nicht extern verifiziert"],
  "missing_information": ["Bestätigter Ansprechpartner", "Aktuelle Tool-Landschaft"],
  "confidence_score": 0.5
}
```

> **Mock-Modus:** Mit dem Standard-`mock`-Provider wird **keine echte
> KI-E-Mail** erzeugt — die Antwort ist deterministisch und dient nur der
> Verifikation der Pipeline (Firmenname gespiegelt, restliche Felder leer,
> `confidence_score` = `1.0`). Für echte Entwürfe `LLM_PROVIDER=anthropic`
> setzen (verursacht API-Kosten).

---

## Tests

```bash
# In der laufenden Backend-Umgebung (Docker):
docker compose run --rm --no-deps backend python -m pytest -q
```

Die Tests decken die Request-/Response-Validierung, das Prompt-Building, den
`LeadResearchService` (mit Mock-Provider) und den API-Endpoint ab.

---

## Nächste Schritte

Die Schichten `domain` und `application` sind bewusst leer und werden in den
folgenden Phasen mit Entities, Use Cases und konkreten Repository-Implementierungen
gefüllt.
