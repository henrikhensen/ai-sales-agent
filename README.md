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
