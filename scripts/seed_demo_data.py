#!/usr/bin/env python3
"""Seed a small, explainable sample dataset for a first Beta walkthrough
(Phase 36: First Customer Beta Package).

Creates, via the *existing*, already-safety-gated HTTP API — never by
writing to the database directly, and never by inventing a parallel code
path — a sample Offer Profile, a sample ICP Profile, a Lead Sourcing
Campaign, and starts one sourcing run against the Mock provider (the
default; never a real scrape). This never contacts anyone, never starts
a Sales Workflow, never creates an external draft, and never sends
anything — it only produces CRM-adjacent sample records a new admin/sales
user can immediately qualify, review, and give feedback on.

Safe to point at any running backend (local Docker Compose by default).
Idempotent-ish: re-running skips creating the sample Offer/ICP again if
one with the same name already exists, but always starts a new sourcing
run (so you can generate more sample candidates on demand).

Usage:
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --api-base-url http://localhost:8000 \\
        --admin-email demo-admin@example.com --admin-password ChangeMe123!

Environment variable equivalents (used when the matching flag is omitted):
    SEED_API_BASE_URL, SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

if sys.stdout.encoding is None or sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

SAMPLE_OFFER_NAME = "Beta Demo Offer — Freight Visibility API"
SAMPLE_ICP_NAME = "Beta Demo ICP — Mittelständische Logistiker"
SAMPLE_CAMPAIGN_NAME = "Beta Demo Campaign — Sample Leads"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-base-url",
        default=os.environ.get("SEED_API_BASE_URL", "http://localhost:8000"),
        help="Base URL of the running backend (default: http://localhost:8000).",
    )
    parser.add_argument(
        "--admin-email",
        default=os.environ.get("SEED_ADMIN_EMAIL", "beta-demo-admin@example.com"),
        help="Account to log in as (registered automatically if it doesn't exist yet).",
    )
    parser.add_argument(
        "--admin-password",
        default=os.environ.get("SEED_ADMIN_PASSWORD", "BetaDemoPassword123!"),
        help="Password for --admin-email.",
    )
    return parser.parse_args()


def _login_or_register(client: httpx.Client, email: str, password: str) -> str:
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if login.status_code == 200:
        print(f"Angemeldet als {email}.")
        return login.json()["access_token"]

    print(f"Login fehlgeschlagen ({login.status_code}) — registriere {email} neu …")
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "role": "admin", "full_name": "Beta Demo Admin"},
    )
    if register.status_code not in (200, 201):
        print(f"Registrierung fehlgeschlagen: {register.status_code} {register.text}")
        sys.exit(1)

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    login.raise_for_status()
    print(f"Neu registriert und angemeldet als {email}.")
    return login.json()["access_token"]


def _find_by_name(items: list[dict], name: str) -> dict | None:
    return next((item for item in items if item.get("name") == name), None)


def _ensure_offer(client: httpx.Client) -> str:
    existing = client.get("/api/v1/sales-strategy/offers").json()
    match = _find_by_name(existing.get("items", []), SAMPLE_OFFER_NAME)
    if match:
        print(f"Offer Profile existiert bereits: {SAMPLE_OFFER_NAME} ({match['id']})")
        return match["id"]

    response = client.post(
        "/api/v1/sales-strategy/offers",
        json={
            "name": SAMPLE_OFFER_NAME,
            "main_value_proposition": (
                "Echtzeit-Sichtbarkeit für Frachtsendungen ohne manuelle Statusanfragen."
            ),
            "description": (
                "Beispiel-Offer für die Beta-Demo — zeigt, wie ein Offer Profile "
                "Personalisierung und Draft-Erstellung beeinflusst."
            ),
            "target_outcome": "Weniger manuelle Status-Nachfragen beim Kunden.",
            "pain_points_solved": ["Fehlende Sendungssichtbarkeit", "Manuelle Statusanfragen"],
            "key_benefits": ["Echtzeit-Tracking", "Automatische Statusupdates"],
            "differentiators": ["API-first", "Keine Hardware nötig"],
            "call_to_action": "Kurzes Gespräch zur Sendungssichtbarkeit vereinbaren?",
            "tone": "professional",
            "language": "de",
        },
    )
    response.raise_for_status()
    offer_id = response.json()["id"]
    print(f"Offer Profile erstellt: {SAMPLE_OFFER_NAME} ({offer_id})")
    return offer_id


def _ensure_icp(client: httpx.Client) -> str:
    existing = client.get("/api/v1/sales-strategy/icp").json()
    match = _find_by_name(existing.get("items", []), SAMPLE_ICP_NAME)
    if match:
        print(f"ICP Profile existiert bereits: {SAMPLE_ICP_NAME} ({match['id']})")
        return match["id"]

    response = client.post(
        "/api/v1/sales-strategy/icp",
        json={
            "name": SAMPLE_ICP_NAME,
            "description": "Beispiel-ICP für die Beta-Demo.",
            "target_industries": ["Logistik", "Spedition"],
            "target_company_sizes": ["50-200"],
            "target_locations": ["Deutschland"],
            "target_pain_points": ["Fehlende Sendungssichtbarkeit"],
            "buying_triggers": ["Wachstum", "Kundenreklamationen zu Statusanfragen"],
            "minimum_fit_score": 60,
        },
    )
    response.raise_for_status()
    icp_id = response.json()["id"]
    print(f"ICP Profile erstellt: {SAMPLE_ICP_NAME} ({icp_id})")
    return icp_id


def _ensure_campaign(client: httpx.Client, icp_id: str, offer_id: str) -> str:
    existing = client.get("/api/v1/lead-sourcing/campaigns").json()
    match = _find_by_name(existing.get("items", []), SAMPLE_CAMPAIGN_NAME)
    if match:
        print(f"Campaign existiert bereits: {SAMPLE_CAMPAIGN_NAME} ({match['id']})")
        return match["id"]

    response = client.post(
        "/api/v1/lead-sourcing/campaigns",
        json={
            "name": SAMPLE_CAMPAIGN_NAME,
            "description": "Beispiel-Kampagne für die Beta-Demo (Mock-Provider).",
            "icp_profile_id": icp_id,
            "offer_profile_id": offer_id,
            # Deliberately no target_industry/target_location filter: the
            # mock provider's small example pool uses English industry
            # names ("Logistics") and mixed locations, so leaving these
            # unset guarantees a demo always gets a handful of sample
            # candidates back regardless of language.
            "max_results": 5,
        },
    )
    response.raise_for_status()
    campaign_id = response.json()["id"]
    print(f"Campaign erstellt: {SAMPLE_CAMPAIGN_NAME} ({campaign_id})")
    return campaign_id


def _start_run(client: httpx.Client, campaign_id: str) -> list[dict]:
    response = client.post(
        f"/api/v1/lead-sourcing/campaigns/{campaign_id}/runs",
        json={"campaign_id": campaign_id, "max_results": 5, "dry_run": False},
    )
    response.raise_for_status()
    body = response.json()
    candidates = body.get("candidates", [])
    print(f"Sourcing Run gestartet — {len(candidates)} Beispiel-Kandidat(en) erzeugt (Mock).")
    return candidates


def main() -> None:
    args = _parse_args()
    with httpx.Client(base_url=args.api_base_url, timeout=30.0) as client:
        token = _login_or_register(client, args.admin_email, args.admin_password)
        client.headers["Authorization"] = f"Bearer {token}"

        offer_id = _ensure_offer(client)
        icp_id = _ensure_icp(client)
        campaign_id = _ensure_campaign(client, icp_id, offer_id)
        candidates = _start_run(client, campaign_id)

    print()
    print("Fertig. Kein Versand, keine echte Kontaktaufnahme wurde ausgelöst.")
    print("Nächste Schritte für den ersten Beta-Kundenlauf:")
    print(f"  1. Lead Qualification öffnen und die {len(candidates)} Kandidat(en) qualifizieren.")
    print("  2. Einen Kandidaten in die Outreach Queue übernehmen.")
    print("  3. Real-World Test Mode für den Kandidaten starten (safe/mock).")
    print("  4. Den erzeugten Draft im Human Review prüfen.")
    print("  5. Feedback im Quality Dashboard hinterlassen.")
    print("Siehe BETA_ONBOARDING.md für den vollständigen Ablauf.")


if __name__ == "__main__":
    main()
