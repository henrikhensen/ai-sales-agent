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

| Methode | Pfad               | Beschreibung                                |
| ------- | ------------------ | ------------------------------------------- |
| GET     | `/`                | Service-Metadaten                           |
| GET     | `/api/v1/health`   | Health-Check inkl. DB- und Redis-Status     |
| GET     | `/docs`            | Interaktive OpenAPI-Dokumentation (Swagger) |

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

## Nächste Schritte

Die Schichten `domain` und `application` sind bewusst leer und werden in den
folgenden Phasen mit Entities, Use Cases und konkreten Repository-Implementierungen
gefüllt.
