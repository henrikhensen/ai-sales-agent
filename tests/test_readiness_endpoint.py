"""Tests for readiness/liveness endpoints:

- GET /api/v1/health (existing; regression only)
- GET /api/v1/ready (new)
- GET /health, GET /ready (unprefixed aliases in backend/main.py)

Runs without a live Postgres/Redis (as this whole suite does elsewhere,
per tests/conftest.py's docstring) — the checks correctly report "down"
rather than crashing, and /ready correctly maps that to HTTP 503.
"""

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_prefixed_health_still_works():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "database" in data["components"]
    assert "redis" in data["components"]


def test_prefixed_ready_reports_status_and_components():
    response = client.get("/api/v1/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert data["components"]["database"]["status"] in ("up", "down")
    assert data["components"]["redis"]["status"] in ("up", "down")
    # 503 exactly when not fully up, 200 exactly when fully up.
    all_up = all(c["status"] == "up" for c in data["components"].values())
    assert response.status_code == (200 if all_up else 503)


def test_root_health_alias_always_returns_200():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_ready_alias_reports_status():
    response = client.get("/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    assert data["status"] in ("ready", "not_ready")
    assert data["database"] in ("up", "down")
    assert data["redis"] in ("up", "down")


def test_root_endpoint_still_works():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_request_id_header_present_on_responses():
    response = client.get("/api/v1/health")
    assert "x-request-id" in {k.lower() for k in response.headers.keys()}
