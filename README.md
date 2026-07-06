# AI Sales Agent

**AI Sales Agent SaaS System** mit FastAPI-Backend, KI-Agenten-Framework
(Analyse- und Entwurfswerkzeuge) und einem Next.js-Dashboard-Frontend.

Das System ist vollständig lauffähig: FastAPI-App, async PostgreSQL-Anbindung,
Redis-Anbindung, Health-Check-Endpoint, fünf KI-Agenten und ein komplettes
Docker-Setup inklusive Frontend.

---

## Tech Stack

| Komponente          | Technologie           |
| -------------------- | --------------------- |
| Backend-Sprache       | Python 3.12            |
| Web Framework         | FastAPI                |
| Datenbank             | PostgreSQL (asyncpg)   |
| Cache / Broker        | Redis                  |
| Validierung           | Pydantic v2            |
| ORM                   | SQLAlchemy 2 (async)   |
| Frontend              | Next.js (App Router)   |
| Frontend-Sprache      | TypeScript / React     |
| Styling               | Tailwind CSS           |
| Container             | Docker + Compose       |

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
├── frontend/                        # Next.js Dashboard (siehe "Frontend Dashboard")
│   ├── app/                         # Seiten (App Router)
│   ├── components/                  # UI-, Layout- und Agenten-Komponenten
│   ├── lib/                         # API-Client & Typen
│   └── Dockerfile
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

Das startet vier Services:

- `backend` — FastAPI auf Port **8000**
- `frontend` — Next.js Dashboard auf Port **3000**
- `postgres` — PostgreSQL auf Port **5432**
- `redis` — Redis auf Port **6379**

Die App wartet dank Healthchecks, bis PostgreSQL und Redis bereit sind. Für
das Frontend ist **keine lokale Node-Installation nötig** — es läuft
vollständig über Docker.

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

### 4. Windows-Kurzbefehle (PowerShell-Skripte)

Für den täglichen Gebrauch auf Windows gibt es fertige Skripte unter
`scripts/`:

```powershell
# Kompletten Stack per Docker bauen und starten
powershell -File scripts\docker-up.ps1

# Stack wieder stoppen
powershell -File scripts\docker-down.ps1

# Backend-Tests ausführen (nutzt .venv)
powershell -File scripts\test.ps1

# Backend + Frontend lokal ohne Docker starten (je eigenes Fenster)
powershell -File scripts\dev.ps1
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
| POST    | `/api/v1/agents/reply-analysis` | Reply Analysis Agent (Antwortanalyse, keine Aktion) |
| POST    | `/api/v1/workflows/sales`     | End-to-End Sales Workflow (kombiniert vier Agenten) |
| GET     | `/api/v1/workflows/sales/runs` | Gespeicherte Sales Workflows auflisten |
| GET     | `/api/v1/workflows/sales/runs/{workflow_id}` | Gespeicherten Sales Workflow abrufen |
| PATCH   | `/api/v1/workflows/sales/runs/{workflow_id}/review-status` | Review-Status ändern (nur interne Prüfung) |
| GET     | `/api/v1/settings/llm/status` | LLM-Provider-Status (aktiver Provider, ob Anthropic konfiguriert ist, nie der Key) |
| POST    | `/api/v1/settings/llm/test`   | LLM-Provider testen (nur Admin; im Mock-Modus kostenlos, siehe „Echte LLM API sicher aktivieren") |
| POST    | `/api/v1/research/website`    | Website Research: eine öffentliche URL abrufen und lesbaren Text extrahieren (siehe „Website Research") |
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

## Echte LLM API sicher aktivieren

Das AI Agent Framework spricht mit einem austauschbaren LLM Provider
(`backend/infrastructure/llm/`). Es gibt zwei Provider:

- **`mock`** (Standard): läuft vollständig offline, produziert deterministische
  Platzhalter-Ausgaben passend zum jeweiligen JSON Schema, und **verursacht
  keinerlei API-Kosten**. Jede Agenten-, Workflow- und Settings-Test-Anfrage
  funktioniert damit ohne jede externe Abhängigkeit oder Konfiguration.
- **`anthropic`** (optional): spricht echte Claude-Modelle über die
  Anthropic API an und **verursacht reale API-Kosten**. Vollständig optional
  — das System läuft ohne diesen Provider genauso gut.

**Relevante `.env`-Variablen** (siehe `.env.example`):

| Variable | Default | Bedeutung |
| --- | --- | --- |
| `LLM_PROVIDER` | `mock` | `mock` oder `anthropic`. |
| `LLM_ENABLE_REAL_CALLS` | `false` | Muss **bewusst** auf `true` gesetzt werden, damit ein echter, kostenpflichtiger Call überhaupt stattfinden kann. |
| `ANTHROPIC_API_KEY` | *(leer)* | Nur nötig für `anthropic`. **Niemals committen.** |
| `ANTHROPIC_MODEL` | `claude-opus-4-8` | Welches Claude-Modell verwendet wird. |
| `LLM_MAX_INPUT_CHARS` | `12000` | Prompts, die länger sind, werden vor dem Versand an Anthropic gekürzt (Mock ignoriert das). |
| `LLM_MAX_OUTPUT_TOKENS` | `1200` | Begrenzt Antwortlänge und Kosten pro echtem Call. |
| `LLM_REQUEST_TIMEOUT_SECONDS` | `30` | Timeout für einen echten Anthropic-Call. |

**So aktivierst du echte Calls (in dieser Reihenfolge):**

1. `LLM_PROVIDER=anthropic` in `.env` setzen.
2. Einen echten Anthropic API Key in `ANTHROPIC_API_KEY` eintragen — **niemals
   in `.env.example`, Code oder einen Commit**. `.env` ist per `.gitignore`
   von Commits ausgeschlossen.
3. Erst zuletzt `LLM_ENABLE_REAL_CALLS=true` setzen.
4. Backend neu starten (`docker compose up -d --build backend` oder lokal
   neu starten), damit die neue Konfiguration geladen wird.

**Sicherheitsmechanismus:** Selbst wenn `LLM_PROVIDER=anthropic` und
`ANTHROPIC_API_KEY` beide gesetzt sind, macht das Backend **keinen einzigen
echten Call**, solange `LLM_ENABLE_REAL_CALLS` nicht explizit `true` ist —
`backend/infrastructure/llm/factory.py` fällt in diesem Fall automatisch und
ohne Fehler auf den Mock Provider zurück (mit einer Warnung im Log, niemals
mit dem Key selbst). Es braucht also immer alle drei Bedingungen gleichzeitig,
damit ein echter, kostenpflichtiger Call möglich wird:

1. `LLM_PROVIDER=anthropic`
2. `ANTHROPIC_API_KEY` gesetzt
3. `LLM_ENABLE_REAL_CALLS=true`

**Wieder auf Mock zurückstellen:** `LLM_PROVIDER=mock` setzen (oder
`LLM_ENABLE_REAL_CALLS=false` lassen/setzen) und das Backend neu starten —
danach laufen wieder alle Agenten und der Sales Workflow vollständig
offline, exakt wie zuvor.

**Fehlerbehandlung bei echten Calls:** `AnthropicLLMProvider`
(`backend/infrastructure/llm/anthropic_provider.py`) fängt jeden bekannten
Fehlerfall der Anthropic SDK ab und wandelt ihn in eine eigene, saubere
Fehlermeldung um — nie stürzt der Server dabei ab, nie landet der API Key in
einer Fehlermeldung oder einem Log:

| Fehlerfall | Verhalten |
| --- | --- |
| Fehlender API Key | Provider wird gar nicht erst gebaut; Factory fällt auf Mock zurück, `POST /settings/llm/test` meldet dies explizit. |
| Rate Limit erreicht | Klare Meldung, HTTP 502 an die aufrufende Route. |
| Timeout | Klare Meldung, HTTP 502. |
| Ungültiges Modell | Klare Meldung mit dem konfigurierten Modellnamen, HTTP 502. |
| Sonstiger API-Fehler (Auth, Bad Request, Server-Fehler) | Klare Meldung, HTTP 502. |
| Netzwerkfehler | Klare Meldung, HTTP 502. |

Jeder der fünf Agenten (Lead Research, Company Intelligence, Personalization,
Email Draft, Reply Analysis) sowie der Sales Workflow laufen über dieselbe
Provider Factory und dieselbe Fehlerbehandlung — im Mock-Modus verhält sich
alles exakt wie zuvor; bei aktivierten echten Calls bleibt jeder Fehler
sauber und ohne Absturz.

**Status abfragen:** `GET /api/v1/settings/llm/status` zeigt, welcher
Provider aktuell tatsächlich aktiv ist, ob Anthropic konfiguriert ist (nur als
`true`/`false` — der Key selbst wird nie zurückgegeben, geloggt oder in
Swagger sichtbar) und ob `LLM_ENABLE_REAL_CALLS` gesetzt ist. Lesbar für
`admin`, `reviewer` und `sales`.

**Provider testen:** `POST /api/v1/settings/llm/test` (nur `admin`) prüft
den aktiven Provider mit einem kurzen, generischen Test-Prompt (keine langen
Prompts, keine sensiblen Daten). Im Mock-Modus (Standard) wird ausschließlich
der Mock Provider getestet — kostenlos, ohne externen Call. Ist
`LLM_PROVIDER=anthropic` gesetzt, aber `LLM_ENABLE_REAL_CALLS` nicht `true`,
antwortet der Endpoint klar mit: *"Real LLM calls are disabled. Enable
LLM_ENABLE_REAL_CALLS=true in .env to test Anthropic."* Fehlt zusätzlich der
API Key, obwohl echte Calls aktiviert sind, antwortet der Endpoint ebenso
klar mit: *"ANTHROPIC_API_KEY is not set..."* — in beiden Fällen ohne einen
echten Call zu versuchen. Ein echter Anthropic-Call passiert ausschließlich,
wenn alle drei oben genannten Bedingungen erfüllt sind.

**Frontend (Settings-Seite):** Zeigt aktiven Provider, ob echte Calls
aktiviert sind, das konfigurierte Modell, einen Safe-Mode-Hinweis und eine
Kostenwarnung, plus den Button „LLM Verbindung testen" (nur für `admin`
sichtbar/wirksam). Der API Key wird im Frontend nirgends angezeigt,
eingegeben oder gespeichert — er kommt ausschließlich aus der Backend-`.env`.

> **Wichtig:**
> - Ein Claude Code- oder Claude.ai-Abo beinhaltet **keine** automatische
>   Nutzung der Anthropic API — dafür ist ein separater API Key mit eigener
>   Abrechnung nötig.
> - `ANTHROPIC_API_KEY` gehört ausschließlich in die lokale `.env`-Datei
>   (per `.gitignore` von Commits ausgeschlossen) — niemals in Code, Commits,
>   Logs oder API-Responses.
> - Echte Calls können **API-Kosten verursachen** und senden die jeweiligen
>   Prompt-Inhalte (Firmenname, Notizen, etc.) an den gewählten Provider.
> - Keine Agenten-, Workflow- oder Settings-Anfrage sendet jemals eine
>   E-Mail oder nimmt automatisch Kontakt auf — unabhängig vom gewählten
>   LLM Provider und unabhängig davon, ob echte Calls aktiviert sind.

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

## Reply Analysis Agent

Der **Reply Analysis Agent** analysiert eingehende Antworten von Leads,
klassifiziert sie objektiv und liefert strukturierte Handlungsvorschläge für
einen menschlichen Sales-Mitarbeiter. Er nutzt dasselbe AI-Agent-Framework und
den konfigurierten LLM-Provider (standardmäßig `mock`).

### Was der Agent macht

- Klassifiziert die Antwort (`classification`): `interested`,
  `meeting_request`, `question`, `objection`, `not_interested`,
  `out_of_office` oder `unclear`.
- Bewertet Sentiment (`positive`/`neutral`/`negative`/`unclear`) und Dringlichkeit
  (`low`/`medium`/`high`/`unclear`).
- Fasst die Antwort zusammen (`summary`) und erkennt Absichten
  (`detected_intent`), offene Fragen (`questions_to_answer`), Einwände
  (`objections_detected`) und Kaufsignale (`buying_signals`).
- Empfiehlt eine konkrete nächste Aktion für einen Menschen
  (`recommended_next_action`) und liefert optional einen **Entwurf** für eine
  Antwort (`suggested_reply`, `suggested_reply_subject`).
- Nennt Bedingungen, unter denen **keine weitere Kontaktaufnahme** erfolgen
  sollte (`do_not_continue_if`), sowie Gründe für die Pflicht zur menschlichen
  Prüfung (`compliance_notes`).
- Markiert fehlende Informationen in `missing_information`;
  `confidence_score` (0.0–1.0) sinkt bei unklaren oder mehrdeutigen Antworten.
- Empfiehlt bei Absage oder Desinteresse ausdrücklich eine **respektvolle,
  drucklose Beendigung** statt aggressiver Folge-Strategien.

### Was der Agent ausdrücklich **nicht** macht

- **Sendet KEINE Antwort automatisch.** `suggested_reply` ist ausschließlich
  ein Entwurf zur menschlichen Prüfung.
- **Bucht KEINE Termine automatisch** und bestätigt keine Meetings — auch wenn
  der Lead einen Termin vorschlägt, wird dies nur erkannt und zur menschlichen
  Terminierung empfohlen.
- **Keine automatische Kontaktaufnahme, kein Spam, keine LinkedIn-Automation.**
- **Keine erfundenen Fakten, Ansprechpartner, Termine oder Zusagen.**
- **Keine Täuschung, keine aggressive Verkaufssprache, keine falschen
  Versprechen.**
- **Keine privaten oder unrechtmäßig beschafften Daten.** Nur Nutzer-Input;
  kein externer Datenabruf.
- Der Firmenname (`company_name`) im Ergebnis stammt immer aus dem Input,
  nicht vom Modell.

> **Hinweis:** Jede Analyse und jeder Antwortentwurf **muss von einem
> Menschen geprüft und freigegeben werden**, bevor irgendeine Aktion
> (Antworten, Terminieren, weitere Kontaktaufnahme) erfolgt. Dieser Agent
> führt selbst niemals eine dieser Aktionen aus.

### Beispiel-Request

```bash
curl -X POST http://localhost:8000/api/v1/agents/reply-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme GmbH",
    "lead_name": "Jane Doe",
    "lead_role": "Leiter Operations",
    "original_email_subject": "Mehr Transparenz in Ihrer Sendungslogistik",
    "original_email_body": "Hallo Frau Doe, ...",
    "reply_text": "Danke für die Nachricht. Können wir nächste Woche kurz telefonieren?",
    "previous_context": "Erstkontakt vor zwei Wochen.",
    "product_or_service_offered": "Sendungs-Sichtbarkeitsplattform",
    "notes": "Wirkt interessiert."
  }'
```

Validierung: `company_name` und `reply_text` sind Pflicht, leere Strings
werden abgelehnt (`422`).

### Beispiel-Response

```json
{
  "company_name": "Acme GmbH",
  "classification": "meeting_request",
  "sentiment": "positive",
  "urgency": "medium",
  "summary": "Lead antwortet positiv und schlägt ein Telefonat vor.",
  "detected_intent": ["Interesse an weiterem Austausch"],
  "recommended_next_action": "Zwei Terminvorschläge durch einen Menschen abstimmen lassen.",
  "suggested_reply": "Hallo Frau Doe, vielen Dank für Ihre Rückmeldung. Passt Ihnen Dienstag oder Mittwoch nächste Woche?",
  "suggested_reply_subject": "Re: Mehr Transparenz in Ihrer Sendungslogistik",
  "questions_to_answer": [],
  "objections_detected": [],
  "buying_signals": ["Bittet aktiv um einen Gesprächstermin"],
  "do_not_continue_if": ["Lead sagt Termin kurzfristig wieder ab", "Lead bittet um keinen weiteren Kontakt"],
  "compliance_notes": ["Entwurf und Terminvorschlag müssen von einem Menschen geprüft und bestätigt werden"],
  "missing_information": ["Bevorzugte Telefonzeit"],
  "confidence_score": 0.75
}
```

> **Mock-Modus:** Mit dem Standard-`mock`-Provider wird **keine echte
> KI-Antwortanalyse** erzeugt — die Antwort ist deterministisch und dient nur
> der Verifikation der Pipeline (Firmenname gespiegelt, `classification`,
> `sentiment` und `urgency` auf dem jeweils ersten zulässigen Wert, restliche
> Felder leer, `confidence_score` = `1.0`). Für echte Analysen
> `LLM_PROVIDER=anthropic` setzen (verursacht API-Kosten).

---

## Website Research

Der Endpoint `POST /api/v1/research/website` (Swagger-Tag `research`,
Rollen: `admin`, `reviewer`, `sales`) ruft eine vom Nutzer angegebene,
öffentlich erreichbare Website ab und extrahiert daraus lesbaren Text —
als eigenständiges Analysewerkzeug, unabhängig von den KI-Agenten. **In
dieser Phase findet kein LLM-Call statt** — es wird nur HTML abgerufen und
in reinen Text umgewandelt, es entstehen also auch keine KI-Kosten.

**Request:**

```json
{
  "url": "https://acme.example.com",
  "max_pages": 1,
  "include_same_domain_links": false
}
```

- `url` (Pflicht): muss `http://` oder `https://` sein.
- `max_pages` (optional, 1–3, Standard `1`): reserviert für ein späteres
  Crawling verlinkter Seiten derselben Domain — **in dieser Phase wird
  immer nur genau die angegebene URL abgerufen**, ein höherer Wert löst
  lediglich eine Warnung in der Antwort aus.
- `include_same_domain_links` (optional, Standard `false`): ebenfalls für
  später reserviert, hat aktuell keine Wirkung.

**Response:**

```json
{
  "url": "https://acme.example.com",
  "final_url": "https://acme.example.com/",
  "domain": "acme.example.com",
  "title": "Acme GmbH — Logistics Software",
  "meta_description": "We build freight visibility software.",
  "extracted_text": "Acme builds visibility software for freight companies...",
  "text_length": 1532,
  "pages_fetched": 1,
  "sources_used": ["https://acme.example.com/"],
  "warnings": []
}
```

**Sicherheitsmechanismen** (`backend/infrastructure/web/fetcher.py`):

- Nur `http`/`https` erlaubt — jedes andere Schema (`ftp://`, `file://`,
  `javascript:` etc.) wird abgelehnt.
- `localhost`, `127.0.0.1`, IPv6-Loopback (`::1`), private Netzwerke
  (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), Link-Local-Adressen
  (inkl. der Cloud-Metadaten-Adresse `169.254.169.254`) und weitere
  interne/reservierte Adressbereiche werden immer blockiert — unabhängig
  von der Konfiguration.
- Timeout, maximale Antwortgröße und maximale Redirect-Anzahl sind
  begrenzt; jeder Redirect wird erneut gegen dieselben Regeln geprüft,
  bevor ihm gefolgt wird.
- Es werden keine Cookies über Anfragen hinweg gespeichert und niemals
  ein Formular abgeschickt — ausschließlich ein einzelner GET-Request pro
  Seite.
- Ein eigener User-Agent identifiziert das Tool gegenüber der Zielseite.

**Was dieses Feature bewusst NICHT tut:**

- **Keine automatische Massenrecherche** — es wird ausschließlich die vom
  Nutzer explizit angegebene URL abgerufen, nie eine Liste oder ein
  automatischer Crawl.
- **Kein LinkedIn-Scraping** und keine sonstige Umgehung von Login/Consent
  — der Fetcher folgt nur öffentlichen, nicht authentifizierten
  Weiterleitungen.
- **Kein Login-Bypass** jeglicher Art.
- **Kein E-Mail-Versand** und keine automatische Kontaktaufnahme.
- **Keine KI-Kosten** — dieser Endpoint ruft in dieser Phase keinen LLM
  Provider auf; die spätere Verknüpfung mit den Analyse-Agenten (z. B. als
  zusätzlicher Kontext für Lead Research) ist eine mögliche künftige Phase.

**Relevante `.env`-Variablen** (siehe `.env.example`):

| Variable | Default | Bedeutung |
| --- | --- | --- |
| `WEBSITE_FETCH_TIMEOUT_SECONDS` | `10` | Timeout pro Abruf. |
| `WEBSITE_FETCH_MAX_BYTES` | `2000000` | Maximale Antwortgröße pro Seite. |
| `WEBSITE_RESEARCH_MAX_PAGES` | `1` | Serverseitige Obergrenze; reserviert für späteres Crawling. |
| `WEBSITE_RESEARCH_USER_AGENT` | `AI-Sales-Agent-WebsiteResearch/1.0` | User-Agent-Header beim Abruf. |

---

## End-to-End Sales Workflow

Der Endpoint `POST /api/v1/workflows/sales` (Swagger-Tag `workflows`)
kombiniert vier bestehende Agenten zu einem einzigen Ablauf: **Lead
Research → Company Intelligence → Personalization → Email Draft**. Jeder
Schritt nutzt denselben konfigurierten LLM-Provider (standardmäßig `mock`);
es wird kein neuer Agent gebaut, sondern die vorhandenen Services aus
`backend/agents/` werden nacheinander aufgerufen und ihre Ausgaben
ineinander gemappt (z. B. fließt die Lead-Research-Zusammenfassung in die
Personalization ein, die Personalization-Strategie in den Email-Entwurf).

Die Antwort enthält die vollständigen Einzelergebnisse aller vier Schritte
sowie eine aggregierte Zusammenfassung: `review_checklist` (konkrete
Prüfpunkte für einen Menschen), `compliance_notes` (stellt ausdrücklich klar,
dass nichts automatisch versendet wurde), `missing_information` (über alle
Schritte gesammelt) und einen gemittelten `confidence_score`.

**Wichtig:**

- **Sendet keine E-Mail, kontaktiert niemanden automatisch und bucht keinen
  Termin.** Der Workflow liefert ausschließlich Analyse und einen Entwurf.
- `human_review_required` ist im Ergebnis immer `true` — menschliche Prüfung
  bleibt für jede tatsächliche Aktion Pflicht.
- Im Mock-Modus (Standard) wird **keine echte KI-Analyse** erzeugt; die
  Antwort ist deterministisch und dient nur der Verifikation der Pipeline.

```bash
curl -X POST http://localhost:8000/api/v1/workflows/sales \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme GmbH",
    "website_url": "https://acme.example.com",
    "industry": "Logistics",
    "product_or_service_offered": "Sendungs-Sichtbarkeitsplattform",
    "sender_name": "John Smith",
    "sender_company": "Beta Vertrieb GmbH",
    "tone": "consultative",
    "language": "German"
  }'
```

---

## Website Research im Sales Workflow

Website Research ist in den `SalesWorkflowService` verdrahtet (die Felder
selbst existieren bereits länger, siehe `SalesWorkflowRequest.use_website_research`
/ `website_research_max_pages` und `SalesWorkflowResponse.website_research*`).

**`use_website_research=true` aktiviert Website Research** für den Lauf:

1. Die in `website_url` angegebene Seite wird über denselben
   SSRF-geschützten `WebsiteResearchService` abgerufen, der auch hinter
   `POST /api/v1/research/website` steckt (siehe „Website Research" oben)
   — mit `max_pages=website_research_max_pages` (1–3) und
   `include_same_domain_links=false`.
2. War der Abruf erfolgreich: `website_research_used=true`,
   `website_research` enthält das vollständige Ergebnis (Titel, Meta
   Description, `extracted_text`, Quellen, Warnungen), und
   `website_research_warnings` übernimmt die Warnungen aus dem
   Research-Ergebnis (z. B. bei Kürzung sehr langer Texte).
3. **`extracted_text` wird für Company Intelligence genutzt** — als
   `website_text`, aber nur, wenn im Request kein eigenes `website_text`
   angegeben wurde. Ein explizit vom Nutzer gesetztes `website_text` hat
   immer Vorrang; es werden nie Fakten erfunden.
4. Schlägt der Abruf aus einem gewöhnlichen Grund fehl (Timeout, HTTP-Fehler,
   zu große Antwort, zu viele Redirects), **bricht der Workflow nicht ab**
   — er läuft mit den vorhandenen Eingaben weiter, setzt
   `website_research_used=false` und hängt eine verständliche Meldung an
   `website_research_warnings` an.
5. Handelt es sich dagegen um einen **Sicherheitsfehler** (die URL ist
   blockiert, z. B. `localhost` oder eine private/interne Adresse), liefert
   der Endpoint eine saubere **`400 Bad Request`** — ohne interne Details
   wie den genauen Host oder Validierungsgrund preiszugeben. Ein bewusst
   blockierter Request ist kein Fall für ein stilles Weiterlaufen.

**Ergebnis wird in Workflow History gespeichert:** `GET
/api/v1/workflows/sales/runs/{workflow_id}` zeigt sowohl die Eingaben
(`input_payload.use_website_research`, `input_payload.website_research_max_pages`)
als auch das Ergebnis (`result_payload.website_research_used`,
`result_payload.website_research`, `result_payload.website_research_warnings`)
— genau wie jeder andere Workflow-Lauf, ohne Sonderbehandlung.

**Wichtig:**

- Website Research selbst macht **keinen LLM-Call** — es wird nur HTML
  abgerufen und in Text umgewandelt (siehe „Website Research" oben). Der
  extrahierte Text wird anschließend ganz normal als Kontext an den
  bestehenden Company-Intelligence-Agenten übergeben, der den konfigurierten
  LLM-Provider nutzt (standardmäßig `mock`, keine echten API-Kosten).
- Der Workflow **sendet weiterhin keine E-Mail** und kontaktiert niemanden
  automatisch — `human_review_required` bleibt immer `true`.
- Workflows ohne `use_website_research` (Standard `false`) laufen exakt wie
  zuvor; der `WebsiteResearchService` wird dann gar nicht erst aufgerufen.

---

## Workflow History

Jeder erfolgreich ausgeführte Sales Workflow wird automatisch in PostgreSQL
gespeichert (Tabelle `workflow_runs`, JSONB für Input/Result). Die
`workflow_id` in der `POST /api/v1/workflows/sales`-Antwort ist die ID dieses
gespeicherten Datensatzes — die Response bleibt dabei vollständig
kompatibel, es ändert sich nur, dass diese ID jetzt real abrufbar ist.

**Neue Endpoints** (Swagger-Tag `workflows`):

| Methode | Pfad | Beschreibung |
| --- | --- | --- |
| GET | `/api/v1/workflows/sales/runs` | Gespeicherte Workflows auflisten (Filter: `company_name`, `review_status`; Paginierung: `limit`, `offset`) |
| GET | `/api/v1/workflows/sales/runs/{workflow_id}` | Einzelnen gespeicherten Workflow inkl. vollständigem Input/Result abrufen |
| PATCH | `/api/v1/workflows/sales/runs/{workflow_id}/review-status` | Internen Review-Status ändern |

Erlaubte `review_status`-Werte: `needs_review` (Standard nach Ausführung),
`reviewed`, `approved`, `rejected`, `archived`.

```bash
# Ergebnis später abrufen
curl http://localhost:8000/api/v1/workflows/sales/runs/<workflow_id>

# Review-Status setzen
curl -X PATCH http://localhost:8000/api/v1/workflows/sales/runs/<workflow_id>/review-status \
  -H "Content-Type: application/json" \
  -d '{"review_status": "approved"}'
```

**Wichtig:**

- **`approved` bedeutet ausschließlich "intern geprüft" — NICHT
  "Versandfreigabe".** Kein Endpoint in diesem Bereich sendet eine E-Mail,
  nimmt Kontakt auf oder bucht einen Termin; es wird ausschließlich der
  Review-Status in der Datenbank aktualisiert.
- Es gibt bewusst kein Feld wie `sent` oder `contacted` — tatsächlicher
  Versand bleibt ein vollständig separater, manueller Schritt außerhalb
  dieses Systems.
- Das Frontend zeigt diese History mittlerweile unter **Workflows → Workflow
  History** an (siehe Abschnitt „Workflow History im Frontend" weiter unten).

---

## CRM Integration für Sales Workflows

Nach jeder erfolgreichen Ausführung von `POST /api/v1/workflows/sales`
schreibt der Workflow automatisch die zugehörigen CRM-Daten weg, zusätzlich
zum bereits bestehenden `workflow_runs`-Eintrag:

- **Company**: wird anhand des Firmennamens gesucht (case-insensitive) und
  bei Bedarf neu angelegt (`companies`-Tabelle).
- **Lead**: wird anhand der Company gesucht (ein bestehender Lead der Firma
  wird wiederverwendet) oder neu angelegt (`leads`-Tabelle, Quelle
  `outbound`).
- **Contact** (optional): wird nur angelegt, wenn im Request ein
  `recipient_name` angegeben wurde — eine reine Rolle (`target_persona`)
  reicht nicht aus, um eine Person zu erzeugen.
- **Email Draft**: der vom Email Draft Agent erzeugte Entwurf wird als
  eigener Datensatz gespeichert (`email_drafts`-Tabelle: `subject_lines`,
  `email_body`, `status="draft"`).
- **Interaction/Activity**: pro Workflow-Lauf wird ein Eintrag mit
  `type="workflow_run"` und `status="draft_created"` am Lead hinterlegt
  (`interactions`-Tabelle).

Der gespeicherte `WorkflowRun` wird anschließend mit den erzeugten
CRM-IDs verknüpft (`company_id`, `lead_id`, optional `contact_id`,
`email_draft_id`) und ist darüber sowohl in der Workflow-History
(`GET /api/v1/workflows/sales/runs/{workflow_id}`) als auch über einen
dedizierten Endpoint abrufbar.

Die `SalesWorkflowResponse` bleibt vollständig abwärtskompatibel und wurde
nur um drei optionale Felder ergänzt: `crm_company_id`, `crm_lead_id`,
`crm_email_draft_id`.

**Neue/erweiterte Endpoints:**

| Methode | Pfad | Beschreibung |
| --- | --- | --- |
| GET | `/api/v1/workflows/sales/runs/{workflow_id}/crm-links` | CRM-Verknüpfungen (`company_id`, `lead_id`, `contact_id`, `email_draft_id`) eines gespeicherten Runs abrufen |
| GET | `/api/v1/contacts` | Kontakte auflisten |
| GET | `/api/v1/interactions` | Interactions/Activities auflisten |
| GET | `/api/v1/email-drafts` | Gespeicherte Email-Entwürfe auflisten |

`GET /api/v1/companies` und `GET /api/v1/leads` existierten bereits und
zeigen jetzt auch die vom Sales Workflow angelegten/wiederverwendeten
Datensätze.

```bash
# Workflow ausführen — legt/aktualisiert Company, Lead, optional Contact,
# Email Draft und Interaction an
curl -X POST http://localhost:8000/api/v1/workflows/sales \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme GmbH",
    "product_or_service_offered": "Sendungs-Sichtbarkeitsplattform",
    "recipient_name": "Jane Doe"
  }'

# CRM-Verknüpfungen des Runs abrufen
curl http://localhost:8000/api/v1/workflows/sales/runs/<workflow_id>/crm-links
```

**Wichtig:**

- **Es wird keine E-Mail gesendet, niemand automatisch kontaktiert und kein
  Termin gebucht.** Der Email Draft wird ausschließlich als Entwurf
  gespeichert (`status="draft"`); es gibt bewusst kein Feld wie `sent` oder
  `sent_at`.
- Menschliche Prüfung bleibt Pflicht — `review_status` auf dem `WorkflowRun`
  ist weiterhin ein rein interner Marker (siehe Abschnitt „Workflow
  History"); auch hier bedeutet `approved` **nicht** "Versandfreigabe".
- Es gibt keine externen CRM-Integrationen, keine LinkedIn-Automation und
  keine API Keys für Dritt-CRMs — alle CRM-Daten liegen ausschließlich in
  der projekteigenen PostgreSQL-Datenbank.
- Der Mock-Provider bleibt Standard; die CRM-Synchronisation selbst ruft
  keine externen Services auf.

---

## CRM Pipeline

Jeder Lead hat zusätzlich zu seinem bestehenden `status` (contacted/
qualified/won/lost) einen eigenen **`pipeline_status`**, der nachzeichnet,
wo der Lead im Sales-Workflow-getriebenen Ablauf steht:

| Wert | Bedeutung |
| --- | --- |
| `new` | Standardwert bei Anlage eines Leads. |
| `research_completed` | Reserviert für eine spätere, feinere Zwischenstufe. |
| `draft_created` | Ein Sales Workflow hat erfolgreich einen Email Draft für diesen Lead erzeugt. |
| `in_review` | Der zugehörige Workflow Run wird gerade menschlich geprüft. |
| `approved` | Ein Mensch hat den Workflow Run intern freigegeben — **löst keinen Versand aus**. |
| `rejected` | Ein Mensch hat den Workflow Run intern abgelehnt. |
| `archived` | Manuell archiviert. |

**Endpoints** (Swagger-Tag `pipeline`):

| Methode | Pfad | Beschreibung |
| --- | --- | --- |
| GET | `/api/v1/crm/pipeline` | Pipeline Board: alle Leads gruppiert nach `pipeline_status`, eine Spalte pro Status (auch leere). |
| PATCH | `/api/v1/crm/leads/{lead_id}/pipeline-status` | Einzelnen Lead in eine andere Pipeline-Stufe verschieben. |

**Automatische Übergänge:**

- Läuft ein Sales Workflow erfolgreich durch, wird der zugehörige Lead
  automatisch auf `draft_created` gesetzt, sobald der Email Draft
  gespeichert wurde (`backend/application/crm/workflow_sync_service.py`).
- Wird der `review_status` eines `WorkflowRun` über
  `PATCH /api/v1/workflows/sales/runs/{workflow_id}/review-status` auf
  `approved` oder `rejected` gesetzt und der Run ist mit einem Lead
  verknüpft, wird derselbe Wert automatisch auch auf dessen
  `pipeline_status` gespiegelt (`PipelineService.sync_from_workflow_review_status`).
  Jede andere Review-Status-Änderung lässt den `pipeline_status`
  unverändert — dieselbe Aktion, die den Workflow Run intern freigibt,
  markiert damit auch den zugehörigen Lead, ohne dass eine zweite manuelle
  Aktion nötig ist.

**Rollen:**

- `admin`: darf die Pipeline sehen und jeden `pipeline_status` setzen.
- `sales`: darf die Pipeline sehen und jeden `pipeline_status` setzen.
- `reviewer`: darf die Pipeline sehen; darf einen Lead nur auf `in_review`,
  `approved` oder `rejected` setzen — die frühen, workflow-getriebenen
  Stufen (`new`/`research_completed`/`draft_created`) und das Archivieren
  bleiben eine Sales-/Admin-Aufgabe.

**Wichtig:**

- Eine Statusänderung — auch auf `approved` — ist ausschließlich internes
  CRM-Bookkeeping. Sie sendet **keine E-Mail**, kontaktiert **niemanden**
  automatisch und ruft **keinen externen Service** auf.
- `approved` bedeutet weiterhin nur, dass ein Mensch den zugehörigen
  Workflow Run intern geprüft hat — genau wie beim bestehenden
  `WorkflowRun.review_status` (siehe „Workflow History").

```bash
curl http://localhost:8000/api/v1/crm/pipeline \
  -H "Authorization: Bearer <access_token>"

curl -X PATCH http://localhost:8000/api/v1/crm/leads/<lead_id>/pipeline-status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d '{"pipeline_status": "in_review"}'
```

---

## Human Review & Approval

Zusätzlich zum Review-Status auf `WorkflowRun`-Ebene (siehe „Workflow
History") können jetzt auch einzelne **Email Drafts** geprüft werden, und
jede Statusänderung sowie jeder Kommentar wird als unveränderlicher
Audit-Trail-Eintrag (`ReviewEvent`) gespeichert.

- **Email Drafts prüfen**: `review_status` eines gespeicherten Email Drafts
  setzen — erlaubt sind `needs_review`, `in_review`, `approved`, `rejected`,
  `changes_requested`, `archived` (Standard: `needs_review`). Optional werden
  `reviewer_name` und ein Kommentar gespeichert.
- **Audit Trail**: Jede Statusänderung erzeugt einen `ReviewEvent`-Eintrag
  (`event_type`: `review_started`, `approved`, `rejected`,
  `changes_requested` oder `archived`) mit vorherigem/neuem Status,
  Kommentar und Prüfer-Name. Kommentare zu einem Workflow Run ohne
  Statusänderung erzeugen einen `comment_added`-Eintrag.
- **Verknüpfung zum Workflow Run**: Ist ein Email Draft einem Workflow Run
  zugeordnet, wird dessen `review_status` beim Prüfen des Drafts automatisch
  mit aktualisiert, damit Workflow History und Email-Draft-Review konsistent
  bleiben.

**Neue Endpoints** (Swagger-Tag `reviews`):

| Methode | Pfad | Beschreibung |
| --- | --- | --- |
| POST | `/api/v1/reviews/email-drafts/{email_draft_id}/status` | Review-Status eines Email Drafts setzen, optional mit Kommentar |
| GET | `/api/v1/reviews/email-drafts/{email_draft_id}/events` | Audit Trail eines Email Drafts abrufen |
| POST | `/api/v1/reviews/workflows/{workflow_id}/comment` | Kommentar zu einem Workflow Run hinzufügen (ändert keinen Status) |
| GET | `/api/v1/reviews/workflows/{workflow_id}/events` | Audit Trail eines Workflow Runs abrufen |

```bash
# Email Draft freigeben (nur interne Prüfung — sendet nichts)
curl -X POST http://localhost:8000/api/v1/reviews/email-drafts/<email_draft_id>/status \
  -H "Content-Type: application/json" \
  -d '{
    "review_status": "approved",
    "reviewer_name": "Henrik",
    "comment": "Entwurf geprüft, aber noch nicht senden."
  }'

# Audit Trail des Email Drafts ansehen
curl http://localhost:8000/api/v1/reviews/email-drafts/<email_draft_id>/events

# Kommentar zu einem Workflow Run hinzufügen
curl -X POST http://localhost:8000/api/v1/reviews/workflows/<workflow_id>/comment \
  -H "Content-Type: application/json" \
  -d '{"reviewer_name": "Henrik", "comment": "Bitte Nutzenargument prüfen."}'
```

**Wichtig:**

- **Approval bedeutet ausschließlich "intern geprüft" — niemals
  "Versandfreigabe".** Kein Endpoint in diesem Bereich sendet eine E-Mail,
  nimmt Kontakt auf oder bucht einen Termin. Es gibt bewusst kein Feld wie
  `sent` oder `contacted` auf irgendeiner Antwort.
- Kommentare dürfen nicht leer oder nur aus Leerzeichen bestehen und sind auf
  2000 Zeichen begrenzt; `reviewer_name` ist optional, aber ebenfalls nicht
  leer, falls angegeben.
- Der Audit Trail ist ausschließlich lesend/anfügend — Events werden nie
  verändert oder gelöscht.
- Menschliche Prüfung bleibt für jede tatsächliche Aktion Pflicht; der
  Mock-Provider bleibt Standard.

---

## Authentication

Das Backend unterstützt lokale Benutzerkonten mit Passwort-Login und
JWT-Access-Tokens. **Kein externer Auth-Provider, kein OAuth** — Registrierung,
Login und Token-Prüfung laufen vollständig lokal in diesem Backend.

**Rollen:** `admin`, `reviewer`, `sales` (Standard bei Registrierung: `sales`).

**Neue Endpoints** (Swagger-Tag `auth` / `users`):

| Methode | Pfad | Beschreibung |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | Neuen Benutzer anlegen (Passwort wird als bcrypt-Hash gespeichert) |
| POST | `/api/v1/auth/login` | Mit E-Mail/Passwort anmelden, liefert einen JWT-Access-Token |
| GET | `/api/v1/auth/me` | Aktuell eingeloggten Benutzer abrufen (`Authorization: Bearer <token>`) |
| GET | `/api/v1/users` | Registrierte Benutzer auflisten — nur für aktive Admin-Konten |

### Benutzer registrieren

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "henrik@example.com",
    "password": "supersecret123",
    "full_name": "Henrik",
    "role": "admin"
  }'
```

### Login ausführen

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "henrik@example.com", "password": "supersecret123"}'
```

Antwort: `{"access_token": "<jwt>", "token_type": "bearer"}`.

### Token verwenden / `/auth/me` testen

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

In Swagger (`/docs`) auf **„Authorize"** klicken und den Token einfügen (ohne
das Wort `Bearer` davor, das setzt Swagger automatisch).

**Wichtig:**

- Passwörter werden ausschließlich als bcrypt-Hash gespeichert — niemals im
  Klartext, auch nicht in Logs oder Fehlermeldungen.
- `JWT_SECRET_KEY` hat nur einen unsicheren Entwicklungs-Standardwert; für
  alles außer einer lokalen Sandbox einen echten zufälligen Wert setzen
  (z. B. `openssl rand -hex 32`) und **niemals committen**.
- **Seit Phase 16A sind CRM-, Workflow-, Review- und User-Endpoints durch
  Rollenprüfung geschützt** (siehe „Roles & Permissions" direkt im Anschluss)
  — nur die Agenten-Endpoints (`/api/v1/agents/*`) bleiben in dieser Phase
  bewusst öffentlich, damit die noch ungeschützten Agenten-Seiten im
  Frontend weiter funktionieren.
- Die Review-Endpoints akzeptieren weiterhin ein optionales `reviewer_name`
  Feld im Request; wird es weggelassen, wird automatisch der Name/E-Mail des
  eingeloggten Nutzers verwendet (ein gültiger Token ist für diese
  Endpoints jetzt ohnehin Pflicht).
- In einer späteren Phase werden auch die Agenten-Endpoints und weitere
  Frontend-Seiten schrittweise hinter Login gestellt.
- Kein externer Auth-Provider, kein OAuth, keine E-Mail-Versendung (auch
  nicht bei Registrierung) — Mock-Provider bleibt Standard.

---

## Roles & Permissions

Seit Phase 16A prüft das Backend nicht nur, ob ein Request authentifiziert
ist, sondern auch, ob die Rolle des eingeloggten Benutzers die angefragte
Aktion erlaubt. Es gibt drei Rollen:

| Rolle | Darf |
| --- | --- |
| `admin` | Alles: User verwalten (`GET /users`), CRM lesen, Workflows starten, Workflow History lesen, Review Status ändern (inkl. `approved`/`rejected`) |
| `reviewer` | Workflow History lesen, Email Drafts lesen, Review Status ändern (inkl. `approved`/`rejected`), Kommentare schreiben — **keine** User-Verwaltung, **keine** CRM-Schreibzugriffe (Companies/Leads anlegen) |
| `sales` | Sales Workflows starten, CRM lesen (Companies/Leads/Contacts/Interactions/Email Drafts), CRM schreiben (Companies/Leads anlegen), Workflow History lesen, Kommentare schreiben — **keine** User-Verwaltung, Review Status **nicht** auf `approved`/`rejected` setzbar |

**Wo das durchgesetzt wird** (Auth-Dependencies in
`backend/api/dependencies/auth.py`: `require_admin_user`,
`require_reviewer_or_admin`, `require_sales_or_admin`,
`require_sales_reviewer_or_admin`, generisch via `require_roles(*roles)`):

| Endpoint(-Gruppe) | Erlaubte Rollen |
| --- | --- |
| `GET /api/v1/users` | `admin` |
| `POST /api/v1/companies`, `POST /api/v1/leads`, `PATCH /api/v1/leads/{id}` | `admin`, `sales` |
| `GET /api/v1/companies`, `/leads`, `/contacts`, `/interactions`, `/email-drafts` | `admin`, `reviewer`, `sales` |
| `POST /api/v1/workflows/sales` | `admin`, `sales`, `reviewer` |
| `GET /api/v1/workflows/sales/runs*` | `admin`, `reviewer`, `sales` |
| `PATCH /api/v1/workflows/sales/runs/{id}/review-status` | `admin`, `reviewer` uneingeschränkt; `sales` außer für `approved`/`rejected` (→ 403) |
| `POST /api/v1/reviews/email-drafts/{id}/status` | `admin`, `reviewer` (`sales` komplett gesperrt → 403) |
| `POST /api/v1/reviews/workflows/{id}/comment`, `GET .../events` | `admin`, `reviewer`, `sales` |
| `POST /api/v1/agents/*` | öffentlich (siehe „Authentication") |

**401 vs. 403:**

- **401 Unauthorized** — kein Token, ein ungültiger/abgelaufener Token, oder
  der zugehörige Benutzer existiert nicht mehr.
- **403 Forbidden** — der Token ist gültig, aber die Rolle (oder der
  deaktivierte Account-Status) erlaubt diese konkrete Aktion nicht.

Fehlerantworten leaken keine internen Details — nur eine kurze,
menschenlesbare Meldung wie `"Insufficient role privileges"`.

> **Wichtig:** Keine Rolle und keine Kombination aus Rollen löst jemals
> einen E-Mail-Versand, eine automatische Kontaktaufnahme oder eine
> LinkedIn-Automation aus. Selbst `admin`, der jeden Review-Status
> (inklusive `approved`) setzen darf, ändert damit ausschließlich einen
> internen Prüf-Marker — Versand bleibt ein separater, manueller Schritt
> außerhalb dieses Systems.

---

## Frontend Dashboard

Das **Frontend** ist ein Next.js-Dashboard, das ausschließlich die
vorhandenen Backend-Endpoints aufruft. Es enthält selbst keine Geschäftslogik,
keine API-Keys und keine Möglichkeit zum automatischen Versand oder zur
automatischen Kontaktaufnahme — alle Agenten bleiben Analyse- oder
Entwurfswerkzeuge, jede Aktion erfordert weiterhin menschliche Freigabe.

### Frontend starten

Mit Docker (empfohlen, keine lokale Node-Installation nötig):

```bash
docker compose up --build
```

Alternativ lokal mit Node.js (≥ 18):

```bash
cd frontend
npm install
npm run dev
```

### Dashboard-URL

```
http://localhost:3000
```

### Agenten im Dashboard testen

Im Dashboard unter **Agenten** (oder direkt über die Sidebar) gibt es für
jeden der fünf Agenten ein eigenes Formular:

- Lead Research — `/agents/lead-research`
- Company Intelligence — `/agents/company-intelligence`
- Personalization — `/agents/personalization`
- Email Draft — `/agents/email-draft`
- Reply Analysis — `/agents/reply-analysis`

Jede Seite ist mit Beispielwerten vorausgefüllt, zeigt Ladezustand und Fehler
sauber an und stellt sowohl eine aufbereitete Zusammenfassung als auch die
vollständige JSON-Rohantwort dar. Ein Hinweisbanner erinnert auf jeder Seite
daran, dass im Mock-Modus keine echte KI-Analyse erzeugt wird.

Die **CRM**-Seite (`/crm`) zeigt Companies, Leads, Contacts, Interactions und
Email Drafts live aus dem Backend (siehe „CRM Integration im Frontend"
weiter unten).

### Unterschied zwischen Swagger und Frontend

| | Swagger (`/docs`) | Frontend-Dashboard (`:3000`) |
| --- | --- | --- |
| Zielgruppe | Entwickler, API-Debugging | Sales-Mitarbeiter, Produktnutzung |
| Eingabe | Rohes JSON | Formulare mit Beispielwerten |
| Darstellung | Rohe JSON-Antwort | Aufbereitete Zusammenfassung + JSON |
| Verwendung | Einzelne Endpoints isoliert testen | Kompletter Workflow über alle Agenten |

Beide sprechen dasselbe Backend an — es gibt keine separate Business-Logik im
Frontend.

### Konfiguration

Die Backend-URL wird über `NEXT_PUBLIC_API_BASE_URL` gesteuert (Standard:
`http://localhost:8000`). Da Formulare direkt aus dem Browser gegen das
Backend senden, muss diese URL vom Browser aus erreichbar sein — im
Docker-Setup ist das der veröffentlichte Host-Port, nicht ein interner
Container-Name.

Damit der Browser das Backend von `localhost:3000` aus aufrufen darf, ist
CORS im Backend über `CORS_ALLOWED_ORIGINS` (Standard:
`http://localhost:3000`) freigeschaltet.

> **Hinweis:** Mock-Provider bleibt Standard — es entstehen keine echten
> API-Kosten. Keiner der Agenten sendet automatisch eine E-Mail, bucht einen
> Termin oder nimmt automatisch Kontakt auf; jede tatsächliche Aktion bleibt
> ein separater, menschlich freizugebender Schritt.

### Sales Workflow im Frontend testen

1. Frontend öffnen: **http://localhost:3000**
2. In der Sidebar unter **Workflows → Sales Workflow** navigieren
   (`/workflows/sales`).
3. Formular ausfüllen — die Felder sind bereits mit Beispielwerten
   vorausgefüllt, Pflichtfelder sind `Firmenname` und
   `Angebotenes Produkt/Service`.
4. Auf **„Workflow starten"** klicken.
5. Ergebnis prüfen: Die Seite zeigt Workflow-Status, Lead Research, Company
   Intelligence, Personalization, Email Draft (nur Entwurf), eine
   **Human Review Checklist**, **Compliance Notes** (stellt ausdrücklich klar,
   dass nichts automatisch versendet wurde), fehlende Informationen und den
   aggregierten Confidence-Score — sowie die vollständige JSON-Rohantwort zum
   Aufklappen.

Wie bei den einzelnen Agenten-Seiten gilt: Im Mock-Modus wird keine echte
KI-Analyse erzeugt, es wird nichts automatisch versendet, und jede
tatsächliche Aktion bleibt ein separater, menschlich freizugebender Schritt.

### Workflow History im Frontend

1. Frontend öffnen: **http://localhost:3000**
2. In der Sidebar unter **Workflows → Workflow History** navigieren
   (`/workflows/history`).
3. Gespeicherte Runs ansehen — optional nach Firmenname oder Review Status
   filtern.
4. Über **„Details ansehen"** einen Run öffnen (`/workflows/history/{workflowId}`).
   Die Detailseite zeigt Workflow-ID, Firmenname, Status, Review Status,
   Confidence Score, das vollständige Ergebnis (Lead Research, Company
   Intelligence, Personalization, Email Draft, Human Review Checklist,
   Compliance Notes), fehlende Informationen sowie Input- und Result-Payload
   als Rohdaten.
5. Review Status ändern: Neuen Status auswählen (`needs_review`, `reviewed`,
   `approved`, `rejected`, `archived`) und auf **„Aktualisieren"** klicken.

> **Hinweis:** Es wird dabei **keine E-Mail gesendet** und **keine
> Kontaktaufnahme** ausgelöst. `approved` bedeutet ausschließlich, dass ein
> Mensch den Run intern geprüft hat — niemals eine Versandfreigabe. Beide
> Seiten weisen zusätzlich sichtbar darauf hin, dass im Mock-Modus die
> Ergebnisse Platzhalter enthalten können.

### CRM Integration im Frontend

Die vom Sales Workflow im Backend gespeicherten CRM-Daten (siehe „CRM
Integration für Sales Workflows" weiter oben) sind auch im Dashboard
sichtbar:

1. Frontend öffnen: **http://localhost:3000**
2. In der Sidebar unter **Übersicht → CRM** navigieren (`/crm`).
3. **Gespeicherte Companies ansehen** — Name, Website/Domain, Branche,
   Erstellungsdatum.
4. **Gespeicherte Leads ansehen** — zugehörige Company-ID, Quelle, Status,
   Score, Erstellungsdatum.
5. **Gespeicherte Email Drafts ansehen** — Company-/Lead-/Workflow-Run-ID,
   Status, erste Betreffzeile und eine gekürzte Vorschau des Entwurfstexts.
   Contacts und Interactions werden in derselben Ansicht ebenfalls angezeigt.
6. Die **Workflow History** (`/workflows/history/{workflowId}`) zeigt
   zusätzlich eine Karte **„CRM-Verknüpfungen"** mit Company-, Lead-,
   optionaler Contact- und Email-Draft-ID des jeweiligen Runs, inklusive
   Link zurück zur CRM-Seite.
7. Nach einem erfolgreichen Lauf des Sales Workflow (`/workflows/sales`)
   zeigt das Ergebnis zusätzlich einen Bereich **„CRM gespeichert"** mit den
   erzeugten Company-, Lead- und Email-Draft-IDs.

> **Hinweis:** Es wird dabei **keine E-Mail gesendet**. Email Drafts sind
> ausschließlich gespeicherte Entwürfe (`status: "draft"`), der Review Status
> eines Workflow-Runs löst keinen Versand aus, und es findet keine
> automatische Kontaktaufnahme statt. Der Mock-Modus bleibt Standard.

### Human Review im Frontend

Das Backend-Review-System (siehe „Human Review & Approval" weiter oben) ist
im Dashboard sichtbar und bedienbar:

1. Frontend öffnen: **http://localhost:3000**
2. In der Sidebar unter **Übersicht → Human Review** navigieren (`/reviews`)
   für eine Übersicht des Review-Prozesses mit Links zu Workflow History und
   CRM.
3. **Email Drafts prüfen**: Auf der CRM-Seite (`/crm`) bei einem Email Draft
   auf **„Review"** klicken. Es öffnet sich ein Bereich mit:
   - **Review Status ändern** — `needs_review`, `in_review`, `approved`,
     `rejected`, `changes_requested` oder `archived` auswählen, optional
     Reviewer-Name und Kommentar eingeben, auf **„Speichern"** klicken.
   - **Review Timeline** — alle bisherigen Review-Ereignisse für diesen
     Email Draft (Statuswechsel, Kommentare) in chronologischer Reihenfolge.
4. **Workflow kommentieren**: Auf der Workflow-History-Detailseite
   (`/workflows/history/{workflowId}`) im Bereich **„Kommentare & Review
   Timeline"** einen Kommentar (optional mit Reviewer-Name) hinzufügen — dies
   ändert keinen Review-Status, sondern ergänzt nur die Audit Timeline des
   Workflow Runs.
5. Erfolg und Fehler werden direkt im jeweiligen Formular angezeigt; die
   Timeline aktualisiert sich automatisch nach dem Speichern.

> **Hinweis:** Es gibt **keinen "Send Email"-Button** und keine Möglichkeit,
> über das Frontend eine E-Mail zu versenden oder automatisch Kontakt
> aufzunehmen. `approved` bedeutet ausschließlich eine interne Freigabe —
> menschliche Prüfung bleibt für jede tatsächliche Aktion Pflicht.

### Frontend Authentication

Das Dashboard nutzt die lokalen Backend-Auth-Endpoints (siehe „Authentication"
weiter oben) für Registrierung, Login und Session. **Kein externer
Auth-Provider, kein OAuth.**

1. **Registrierung**: `/register` öffnen, E-Mail, Passwort (mind. 8 Zeichen),
   optional Name und Rolle (`admin`, `reviewer`, `sales`) eingeben. Nach
   erfolgreicher Registrierung wird automatisch eingeloggt und zum Dashboard
   weitergeleitet.
2. **Login**: `/login` öffnen, E-Mail und Passwort eingeben. Der
   Access-Token wird lokal gespeichert (`localStorage`) und danach automatisch
   als `Authorization: Bearer <token>` an alle Backend-Anfragen angehängt.
3. **Eingeloggter Zustand**: Der Header zeigt Name/E-Mail und Rolle des
   aktuellen Nutzers sowie einen **Logout**-Button. Ohne Login zeigt der
   Header stattdessen Links zu **Login** und **Registrieren**.
4. **Geschützte Seiten**: Dashboard, CRM, Workflows (Übersicht, Sales
   Workflow, Workflow History) und Human Review prüfen beim Laden, ob ein
   gültiger Token vorhanden ist. Ohne Token — oder wenn das Backend
   `/api/v1/auth/me` mit 401 beantwortet (z. B. abgelaufener Token) — wird der
   Token gelöscht und automatisch zu `/login` weitergeleitet.
5. **Logout**: Löscht den gespeicherten Token; geschützte Seiten leiten beim
   nächsten Laden automatisch zu `/login` weiter.

**Backend Auth Endpoints:** `POST /api/v1/auth/register`,
`POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `GET /api/v1/users`
(admin-only) — siehe Abschnitt „Authentication" für Details und curl-Beispiele.

> **Hinweis:** Dies ist eine **lokale Authentifizierung für den MVP** —
> `localStorage` ist für ein produktives Deployment keine sichere
> Session-Strategie (kein Schutz vor XSS-Token-Diebstahl, kein
> Server-seitiges Session-Invalidieren). Für Produktion sollte später eine
> sicherere Strategie geprüft werden (z. B. httpOnly-Cookies mit
> CSRF-Schutz, kürzere Token-Laufzeiten, Refresh-Tokens). Agenten-Seiten und
> die Einstellungsseite sind bewusst weiterhin ohne Rollenprüfung erreichbar
> (siehe „Frontend Roles & Permissions") — weitere Seiten und Endpoints
> werden schrittweise in künftigen Phasen abgesichert.

---

## Frontend Roles & Permissions

Seit Phase 16B steuert das Frontend zusätzlich zum Backend (siehe „Roles &
Permissions" oben), welche Navigation, Seiten und UI-Aktionen ein Nutzer
sieht — abhängig von seiner Rolle (`admin`, `reviewer`, `sales`). Das
Frontend verlässt sich dabei nie allein auf diese Prüfung: Das Backend
setzt dieselbe Rollen-Matrix unabhängig durch, sodass eine falsche oder
umgangene Frontend-Prüfung niemals echten Zugriff gewährt — sie kann
höchstens etwas fälschlich verstecken, nie fälschlich freigeben.

**Sichtbare Bereiche pro Rolle** (Sidebar-Navigation):

| Rolle | Sichtbare Bereiche |
| --- | --- |
| `admin` | Dashboard, CRM, Human Review, Agenten, Workflows (Übersicht), Sales Workflow, Workflow History, **Users/Admin** |
| `reviewer` | Dashboard, CRM, Human Review, Agenten, Workflow History — **keine** Workflows-Seiten zum Starten, **keine** User-Verwaltung |
| `sales` | Dashboard, CRM, Agenten, Sales Workflow, Workflow History — **keine** Human Review, **keine** User-Verwaltung |

Implementiert über `frontend/lib/roles.ts` (`isAdmin`, `isReviewer`,
`isSales`, `hasRole`, `canViewUsers`, `canViewCRM`, `canRunSalesWorkflow`,
`canViewWorkflowHistory`, `canManageReviews`, `canApproveReviews`), die die
Sidebar filtern und von `frontend/components/auth/RequireRole.tsx` auf
Seitenebene wiederverwendet werden.

**Seitenschutz:**

- Nicht eingeloggt → automatische Weiterleitung zu `/login` (wie bisher via
  `RequireAuth`).
- Eingeloggt, aber falsche Rolle → **„Zugriff verweigert"**-Anzeige
  (`frontend/components/auth/AccessDenied.tsx`) mit aktueller Rolle und
  Link zurück zum Dashboard — kein Redirect-Loop, kein Logout.
- `/users` ist komplett neu (Phase 16B) und nur für `admin` sichtbar; ruft
  `GET /api/v1/users` auf und zeigt E-Mail, Name, Rolle, Status und
  Erstellungsdatum. Liefert das Backend dennoch 403 (z. B. weil die Rolle
  sich seit dem Login geändert hat), zeigt die Seite dieselbe „Zugriff
  verweigert"-Anzeige statt eines rohen Fehlers.
- `/workflows` (Übersicht) und `/workflows/sales` sind auf `admin` und
  `sales` beschränkt; `/reviews` ist auf `admin` und `reviewer`
  beschränkt. `/crm` und `/workflows/history` bleiben für alle drei Rollen
  offen, da das Backend dort allen dreien Lesezugriff gewährt.

**Review-UI:**

- Auf der CRM-Seite sieht `sales` bei einem Email Draft nur die Review
  Timeline (read-only) — das Formular zum Ändern des Review-Status wird
  ausgeblendet, weil das Backend diesen Endpoint für `sales` vollständig
  sperrt (nicht nur bestimmte Werte).
- Auf einer Workflow-Detailseite darf `sales` das Formular weiterhin
  nutzen, aber die Optionen `approved` und `rejected` werden aus der
  Auswahl entfernt (das Backend akzeptiert bei `sales` nur die übrigen
  Status) — mit einem erklärenden Hinweistext direkt im Formular.
- Kommentare bleiben für alle drei Rollen möglich.

**401 vs. 403 im Frontend:**

- **401** (kein/ungültiger/abgelaufener Token): `lib/api.ts` löscht den
  gespeicherten Token automatisch und benachrichtigt den `AuthProvider`,
  der den eingeloggten Nutzer zurücksetzt — dadurch leiten `RequireAuth`
  und `RequireRole` beim nächsten Render automatisch zu `/login` weiter.
- **403** (gültiger Token, falsche Rolle): Es wird **nicht** ausgeloggt.
  Ganze Seiten zeigen „Zugriff verweigert"; einzelne Formulare (z. B. ein
  Review-Status-Update) zeigen stattdessen die Backend-Fehlermeldung direkt
  im Formular an.

> **Wichtig:** Keine Rolle — auch nicht `admin` — löst im Frontend jemals
> einen E-Mail-Versand, eine automatische Kontaktaufnahme oder eine
> LinkedIn-Automation aus. Es gibt keinen "Senden"-Button. "Approved"
> bedeutet ausschließlich eine interne Freigabe.

---

## LLM Provider Settings im Frontend

Die Seite **Einstellungen** (`/settings`) zeigt den LLM-Provider-Status live
aus dem Backend an (`GET /api/v1/settings/llm/status`, siehe auch „Echte LLM
API sicher aktivieren" oben) und erlaubt Admins einen sicheren
Verbindungstest (`POST /api/v1/settings/llm/test`).

**Settings öffnen:** In der Sidebar unter „Einstellungen" — sichtbar für alle
eingeloggten Rollen (`admin`, `reviewer`, `sales`), da das Backend den
Status-Endpoint für alle drei freigibt.

**Was dort geprüft werden kann:**

- **Mock-Modus:** Badge „Mock Mode Active" + „No API Costs", wenn der Mock
  Provider aktiv ist (Standard) — keine echten API-Kosten, keine echte
  KI-Analyse.
- **Real Calls Status:** Feld „Real Calls Enabled" und ein deutlicher
  Hinweis:
  - `false` (Standard): *„Echte LLM-Aufrufe sind deaktiviert. Es entstehen
    keine API-Kosten durch Agenten-Ausführung."*
  - `true`: deutliche Warnung *„Echte LLM-Aufrufe sind aktiviert. Agenten
    können API-Kosten verursachen."*
- **Anthropic Configured Status:** zeigt nur `Ja`/`Nein`, ob
  `ANTHROPIC_API_KEY` serverseitig gesetzt ist — der Key selbst wird an
  keiner Stelle im Frontend angezeigt, abgefragt oder gespeichert.
- **Active Provider** und **Anthropic Model**: welcher Provider tatsächlich
  aktiv ist und welches Modell konfiguriert wäre.
- Direkt sichtbar: „Mock Provider ist kostenlos und sicher.", „Echte LLM
  Calls können API-Kosten verursachen.", „Echte LLM Calls senden Inhalte an
  den gewählten Provider.", „Es werden keine E-Mails automatisch versendet."

**Test-Button „LLM Verbindung testen":**

- Nur für `admin` sichtbar und nutzbar — `reviewer`/`sales` sehen an
  gleicher Stelle den Hinweis „Nur Admin-Konten dürfen den LLM Provider
  testen." (die Seite selbst bleibt für sie lesbar).
- Verlässt sich vollständig auf die Backend-Sicherheitsprüfung: Meldet das
  Backend `real_calls_enabled=false`, führt der Klick **keinen** echten,
  kostenpflichtigen Call aus, sondern zeigt direkt die vom Backend
  gelieferte Erklärung an.
- Zeigt einen Ladezustand während der Anfrage und danach entweder das
  Testergebnis (Provider, Erfolg, Meldung) oder eine saubere Fehlermeldung
  — nie einen API Key.

> **Wichtig:**
> - Es gibt im Frontend keine Möglichkeit, einen API Key einzugeben,
>   anzuzeigen oder zu speichern — das bleibt ausschließlich Sache der
>   Backend-`.env`-Datei.
> - Ein Claude Code- oder Claude.ai-Abo ist getrennt von der Anthropic-API-
>   Nutzung dieser App — für `LLM_PROVIDER=anthropic` wird ein eigener,
>   separat abgerechneter API Key benötigt.
> - Weder der Status-Abruf noch der Test-Button lösen jemals einen
>   E-Mail-Versand oder eine automatische Kontaktaufnahme aus.

---

## Website Research im Frontend

Seit Phase 18B gibt es eine eigene Seite für Website Research
(`/research/website`, Backend-Endpoint `POST /api/v1/research/website`,
siehe auch „Website Research" oben).

**Frontend öffnen:** In der Sidebar unter **Research → Website Research** —
sichtbar für alle eingeloggten Rollen (`admin`, `reviewer`, `sales`), da das
Backend diesen Endpoint für alle drei freigibt. Alternativ über die
Übersichtsseite `/research`.

**URL eingeben:** Im Formular eine öffentlich erreichbare `http(s)`-URL
eintragen, optional `Max. Seiten` (1–3, reserviert für ein späteres
Crawling — aktuell wird immer nur die eine angegebene URL abgerufen) und die
Checkbox „Links derselben Domain einbeziehen" (ebenfalls ohne Wirkung in
dieser Phase). Klick auf **„Website analysieren"** sendet die Anfrage.

**Ergebnis anzeigen:** Nach erfolgreichem Abruf zeigt die Seite URL, Final
URL, Domain, Title, Meta Description, Textlänge, Anzahl abgerufener Seiten,
die tatsächlich verwendeten Quellen sowie etwaige Warnungen (z. B. bei
Kürzung sehr langer Texte) — und darunter den vollständigen extrahierten
Text in einem gut lesbaren, scrollbaren Bereich. Schlägt der Abruf fehl
(z. B. weil die Backend-Sicherheitsprüfung eine private/interne Adresse
blockiert hat), erscheint die Backend-Fehlermeldung direkt im Ergebnisbereich.

Direkt auf der Seite sichtbar (identisch zu den Backend-Garantien):

- „Website Research ruft nur die vom Nutzer eingegebene öffentliche URL ab."
- „Es findet kein LLM Call statt."
- „Es entstehen keine KI-API-Kosten."
- „Kein LinkedIn Scraping."
- „Keine automatische Kontaktaufnahme."

> **Wichtig:** Dieser Endpoint ruft in dieser Phase keinen LLM Provider auf
> — weder Mock noch Anthropic — und verursacht daher unabhängig von der
> `LLM_PROVIDER`-Konfiguration keinerlei KI-Kosten. Es gibt hier keinen
> „Senden"-Button und keine automatische Kontaktaufnahme; das Ergebnis ist
> ausschließlich zur menschlichen Durchsicht gedacht.

---

## Website Research im Sales Workflow Frontend

Die Seite **Sales Workflow** (`/workflows/sales`) hat jetzt eine eigene
Website-Research-Sektion, direkt unter dem Feld „Website-URL".

**Checkbox aktivieren:** „Website Research verwenden" ankreuzen, dann
erscheint zusätzlich die Auswahl **„Max Pages"** (1–3, Standard `1`,
reserviert für ein späteres Crawling — aktuell wird immer nur die
angegebene URL abgerufen).

**`website_url` eingeben:** Ist die Checkbox aktiviert, aber keine
Website-URL ausgefüllt, sendet das Formular die Anfrage **nicht** und zeigt
stattdessen direkt eine klare Fehlermeldung: *„Website-URL ist erforderlich,
wenn Website Research aktiviert ist."*

**Workflow starten:** Klick auf „Workflow starten" sendet
`use_website_research` und `website_research_max_pages` zusätzlich zu den
bestehenden Feldern an `POST /api/v1/workflows/sales`.

**Website-Research-Ergebnis ansehen:** War Website Research Teil des Laufs,
erscheint in der Ergebnisanzeige ein eigener Abschnitt **„Website
Research"** mit einem Badge („Website Research verwendet" /„nicht
verwendet"), etwaigen Warnungen, sowie — bei erfolgreichem Abruf — Domain,
Title, Meta Description, Textlänge, Anzahl abgerufener Seiten, den
tatsächlich verwendeten Quellen und einer Vorschau des extrahierten Texts.
Konnte Website Research nicht erfolgreich abgeschlossen werden, erscheint
stattdessen der Hinweis: *„Website Research wurde nicht verwendet oder
konnte nicht erfolgreich abgeschlossen werden."* — der restliche Workflow
läuft in diesem Fall trotzdem normal weiter (siehe „Website Research im
Sales Workflow" oben).

Direkt neben der Checkbox sichtbar:

- „Website Research ruft nur die angegebene öffentliche URL ab."
- „Kein LinkedIn Scraping."
- „Kein LLM Call durch Website Research."
- „Keine E-Mail wird versendet."
- „Keine automatische Kontaktaufnahme."

> **Wichtig:** Website Research selbst macht keinen LLM-Call — nur der
> anschließende, bereits bestehende Company-Intelligence-Schritt nutzt den
> konfigurierten LLM-Provider (standardmäßig `mock`, keine echten
> API-Kosten). Es gibt auch hier keinen „Senden"-Button.

---

## CRM Pipeline Frontend

**CRM → Pipeline öffnen:** In der Sidebar unter „CRM Pipeline"
(`/crm/pipeline`) — sichtbar für dieselben Rollen wie die bestehende
CRM-Seite (`admin`, `reviewer`, `sales`), da das Backend
`GET /api/v1/crm/pipeline` für alle drei freigibt.

**Leads nach Status sehen:** Die Seite zeigt sieben Spalten (New, Research
Completed, Draft Created, In Review, Approved, Rejected, Archived), jede
mit der Anzahl enthaltener Leads. Jede Lead-Karte zeigt Lead-ID, Company
(aufgelöst über die bestehenden CRM-Companies, sonst „Nicht verfügbar"),
Score, Erstellt- und Aktualisiert-Zeitpunkt — fehlende Werte erscheinen
konsequent als „Nicht verfügbar" statt leer oder als Fehler.

**Pipeline Status ändern:** Jede Karte hat eine eigene Statusauswahl plus
einen „Status aktualisieren"-Button. Ein Klick ruft
`PATCH /api/v1/crm/leads/{lead_id}/pipeline-status` auf, zeigt währenddessen
einen Ladezustand, bestätigt Erfolg mit einem kurzen Hinweis und lädt
danach die komplette Pipeline neu, damit alle Spalten aktuell bleiben.
Schlägt die Anfrage fehl, erscheint eine saubere Fehlermeldung direkt auf
der betroffenen Karte — bei einer `403`-Antwort immer der feste Text
„Keine Berechtigung für diese Aktion.“, ohne dass der Nutzer ausgeloggt
wird.

**Rollen:**

- `admin` und `sales`: sehen die Pipeline und dürfen jeden Status setzen.
- `reviewer`: sieht die Pipeline; die Statusauswahl zeigt nur `in_review`,
  `approved` und `rejected` an — genau die Werte, die das Backend für
  diese Rolle erlaubt.

Direkt auf der Seite sichtbar:

- „Pipeline-Status löst keinen E-Mail-Versand aus."
- „Approved bedeutet interne Prüfung, nicht Versand."
- „Keine automatische Kontaktaufnahme."
- „Email Drafts bleiben Entwürfe."

> **Wichtig:** Eine Statusänderung — auch auf `approved` — sendet
> **keine E-Mail** und kontaktiert **niemanden** automatisch. Es gibt hier
> keinen „Senden"-Button; `approved` bedeutet ausschließlich, dass ein
> Mensch den zugehörigen Workflow Run intern geprüft hat (siehe „CRM
> Pipeline" oben).

---

## Entwickler-Commands

Alle Befehle gehen vom Projekt-Root aus.

| Zweck | Befehl |
| --- | --- |
| Backend-Tests ausführen (Docker) | `docker compose run --rm --no-deps backend python -m pytest -q` |
| Backend-Tests ausführen (lokal, `.venv`) | `.venv\Scripts\python.exe -m pytest -q` bzw. `powershell -File scripts\test.ps1` |
| Frontend-Build prüfen | `cd frontend; npm install; npm run build` |
| Frontend-Typecheck | `cd frontend; npm run typecheck` |
| Docker-Stack starten | `docker compose up --build` bzw. `powershell -File scripts\docker-up.ps1` |
| Docker-Stack stoppen | `docker compose down` bzw. `powershell -File scripts\docker-down.ps1` |
| Logs ansehen (alle Services) | `docker compose logs -f` |
| Logs ansehen (nur Backend) | `docker compose logs -f backend` |
| Health-Check aufrufen | `curl http://localhost:8000/api/v1/health` |
| Swagger öffnen | Browser → `http://localhost:8000/docs` |
| Dashboard öffnen | Browser → `http://localhost:3000` |

Die Tests decken die Request-/Response-Validierung, das Prompt-Building, die
Services (mit Mock-Provider) und die API-Endpoints aller fünf Agenten sowie
Regressionstests für Health-, CRM- und bestehende Agent-Endpoints ab.

**CI:** `.github/workflows/ci.yml` führt bei jedem Push auf `main` und jedem
Pull Request automatisch Backend-Tests und den Frontend-Build aus — ganz ohne
Secrets und ohne Deployment.

---

## Sicherheit & Production Readiness

Diese Phase bereitet das Projekt für Produktion vor — sie deployt **nichts**
automatisch in eine Cloud und aktiviert **keine** kostenpflichtigen Dienste.

**Warum niemals API-Keys committen:**
Ein committeter API-Key ist ab dem Push öffentlich kompromittiert — auch nach
dem Löschen bleibt er in der Git-Historie sichtbar und muss beim Provider
widerrufen werden. Deshalb:

- `.env` ist in `.gitignore` (Backend) und `frontend/.gitignore` (Frontend)
  ausgeschlossen und darf **niemals** committet werden.
- Nur `.env.example` / `frontend/.env.example` werden versioniert — sie
  enthalten ausschließlich Platzhalterwerte, keine echten Secrets.
- `ANTHROPIC_API_KEY` bleibt standardmäßig leer (`LLM_PROVIDER=mock`); ein
  echter Key ist nur nötig, wenn bewusst `LLM_PROVIDER=anthropic` gesetzt
  wird (siehe Hinweise in den Agenten-Abschnitten oben — verursacht Kosten).
- Das Frontend enthält grundsätzlich keine Secrets: Alles unter
  `NEXT_PUBLIC_*` landet im Browser-Bundle und ist damit öffentlich einsehbar
  — genau deshalb steht dort nur die (nicht-geheime) Backend-URL.

**Bereits umgesetzt:**

- CORS ist über `CORS_ALLOWED_ORIGINS` konfigurierbar; Standardwert ist eine
  konkrete Origin (`http://localhost:3000`), keine Wildcard. Bei
  `APP_ENV=production` mit `CORS_ALLOWED_ORIGINS=*` loggt das Backend beim
  Start eine Warnung.
- Ein globaler Exception-Handler loggt unerwartete Fehler vollständig
  serverseitig, gibt dem Client aber nur `{"detail": "Internal server error"}`
  zurück — keine Stacktraces oder internen Details nach außen.
- Einfache Security-Header (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`) werden auf jede Antwort gesetzt.
- Strukturiertes Logging auf stdout (`backend/shared/logging.py`) mit
  Startup-/Shutdown-Logs und einem Redaction-Filter, der Log-Zeilen mit
  Schlüsselwörtern wie `api_key`, `password`, `token`, `secret` abfängt.
- Docker-Images laufen als Non-Root-User und haben eigene `HEALTHCHECK`s.

**Noch nicht umgesetzt** (siehe [`docs/PRODUCTION_CHECKLIST.md`](docs/PRODUCTION_CHECKLIST.md)):
Authentifizierung/Autorisierung, Rate Limiting, externes Error-Tracking,
Datenbank-Migrationen (Alembic), Backups. Für eine spätere Cloud-Bereitstellung
siehe [`docs/DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md) und die
produktionsnahe, eigenständige Compose-Datei `docker-compose.prod.yml`
(`docker compose -f docker-compose.prod.yml --env-file .env up --build -d`).

---

## Troubleshooting

**Docker nicht erreichbar / "Cannot connect to the Docker daemon"**
Docker Desktop läuft nicht oder startet noch. Docker Desktop öffnen, warten
bis der Wal-Status "Running" ist, dann erneut versuchen.

**Port 8000 ist belegt**
Ein anderer Prozess (oft ein vorheriger `uvicorn`) blockiert den Port.
Prüfen: `netstat -ano | findstr :8000`, den Prozess über die PID beenden
(`taskkill /PID <pid> /F`), oder in `docker-compose.yml` einen anderen
Host-Port mappen (z. B. `"8001:8000"`).

**Port 3000 ist belegt**
Analog zu Port 8000: `netstat -ano | findstr :3000` und den blockierenden
Prozess beenden, oder den Frontend-Port in `docker-compose.yml` ändern.
Achtung: Wird der Host-Port geändert, muss `NEXT_PUBLIC_API_BASE_URL`
weiterhin auf den tatsächlichen Backend-Port zeigen.

**`ERR_CONNECTION_REFUSED` im Browser**
Das Backend läuft nicht oder ist noch nicht bereit. Prüfen:
`docker compose ps` (Status "healthy"?), `docker compose logs backend`, und
ob `curl http://localhost:8000/api/v1/health` antwortet. Zeigt das Dashboard
"Backend: offline", obwohl das Backend läuft, ist meist `CORS_ALLOWED_ORIGINS`
falsch gesetzt — Browser-Anfragen unterliegen CORS, `curl` nicht.

**`.venv` fehlt oder ist kaputt**
```powershell
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
```
Falls dabei native Pakete (z. B. `pydantic-core`, `asyncpg`) aus dem
Quellcode kompiliert werden statt ein fertiges Wheel zu laden, ist meist die
installierte Python-Version zu neu für die gepinnten Paketversionen — Python
**3.12** verwenden (siehe README-Kopf), nicht die jeweils neueste Version.

**Claude Code nutzt API-Billing statt Abo**
Das betrifft die Nutzung von Claude Code selbst, nicht dieses Projekt: Mit
`/login` in Claude Code prüfen, ob ein Claude-Pro/Max-Abo-Konto aktiv ist statt
eines reinen API-Konsolen-Kontos. Ist ein API-Konto verbunden, wird jede
Anfrage nach API-Preisen statt über das Abo abgerechnet — im Zweifel über
`claude.ai/settings` nachsehen, welches Konto verbunden ist.

---

## Nächste Schritte

Bereits umgesetzt: CRM Core, AI-Agent-Framework mit fünf Agenten (Lead
Research, Company Intelligence, Personalization, Email Draft, Reply
Analysis), End-to-End Sales Workflow mit Workflow History und CRM-Integration
(Company/Lead/Contact/Email-Draft/Interaction-Sync, siehe „CRM Integration
für Sales Workflows"), Human Review & Approval mit Audit Trail, lokale
Authentication mit JWT (siehe „Authentication") sowie Role-Based Access
Control für CRM-, Workflow-, Review- und User-Endpoints (siehe „Roles &
Permissions"), Next.js-Dashboard, Docker-Setup für Dev und produktionsnahes
Overlay, CI-Pipeline, strukturiertes Logging und Basis-Security-Härtung.

Mögliche nächste Schritte:

- Agenten-Endpoints (`/api/v1/agents/*`) und die zugehörigen
  Frontend-Seiten ebenfalls hinter Login/Rollen stellen (aktuell bewusst
  noch öffentlich, siehe „Roles & Permissions")
- Rollenbasierte UI-Anpassungen im Frontend (z. B. Buttons für `approved`/
  `rejected` für `sales`-Nutzer ausblenden, statt nur serverseitig 403 zu
  liefern)
- Rate Limiting vor den Agenten-Endpoints
- Alembic-Migrationen statt `create_all`
- Create/Update-Endpoints für Contacts und Interactions (bisher nur
  lesend/listend über den Sales Workflow befüllt)
- Externes Error-Tracking (z. B. Sentry)
- Echtes Cloud-Deployment nach expliziter, bewusster Freigabe (siehe
  `docs/DEPLOYMENT_GUIDE.md`)
