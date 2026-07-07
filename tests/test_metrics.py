"""Tests for backend/shared/metrics.py and the /api/v1/metrics endpoint's
ENABLE_METRICS gating and admin-only access.

The endpoint's entity counts (workflow_run_count, etc.) query the real
database directly via SQLAlchemy, so — like other DB-backed behavior in
this project — that part is exercised via Docker Compose rather than
pytest. What's tested here needs no live database: the in-memory counters
module, the disabled-by-default gating (returns 404 before ever touching
the database), and role gating.
"""

import uuid

from fastapi.testclient import TestClient

from backend.api.v1.dependencies import get_user_repository
from backend.api.v1.schemas.system import MetricsResponse
from backend.main import app
from backend.shared import metrics
from tests.conftest import FakeUserRepository

client = TestClient(app)


def _returning(fake):
    def _get():
        return fake

    return _get


def _login_as(role: str) -> str:
    email = f"{role}-{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpassword123", "role": role},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "testpassword123"},
    )
    return login.json()["access_token"]


def _auth_header(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {_login_as(role)}"}


# -- in-memory counters -----------------------------------------------------


def test_record_request_counts_requests_and_errors():
    metrics.reset_metrics()
    metrics.record_request(200, 10.0)
    metrics.record_request(404, 5.0)
    metrics.record_request(500, 20.0)

    snapshot = metrics.get_request_metrics()
    assert snapshot.request_count == 3
    assert snapshot.request_error_count == 2
    assert snapshot.total_duration_ms == 35.0


def test_increment_counters():
    metrics.reset_metrics()
    metrics.increment_llm_test_count()
    metrics.increment_llm_test_count()
    metrics.increment_do_not_contact_block_count()

    counters = metrics.get_counters()
    assert counters.llm_test_count == 2
    assert counters.do_not_contact_block_count == 1


def test_reset_metrics_clears_everything():
    metrics.record_request(200, 1.0)
    metrics.increment_llm_test_count()
    metrics.reset_metrics()

    assert metrics.get_request_metrics().request_count == 0
    assert metrics.get_counters().llm_test_count == 0


def test_metrics_response_schema_has_no_personal_data_fields():
    """Defensive check: every field is a plain count or timing — none
    suggests storing an actual email address, name, or message body/content
    (as opposed to e.g. "email_draft_count", which just counts rows)."""
    forbidden_substrings = ("_body", "content", "address", "phone", "from_", "to_")
    for field_name in MetricsResponse.model_fields:
        lowered = field_name.lower()
        assert not any(bad in lowered for bad in forbidden_substrings), field_name
        assert field_name.endswith(("_count", "_time_ms"))


# -- endpoint gating ----------------------------------------------------------


def test_metrics_endpoint_without_token_returns_401():
    response = client.get("/api/v1/metrics")
    assert response.status_code == 401


def test_metrics_endpoint_disabled_by_default_returns_404_for_admin(monkeypatch):
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    try:
        response = client.get("/api/v1/metrics", headers=_auth_header("admin"))
        assert response.status_code == 404
    finally:
        app.dependency_overrides.pop(get_user_repository, None)


def test_metrics_endpoint_blocked_for_non_admin():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    try:
        for role in ("sales", "reviewer"):
            response = client.get("/api/v1/metrics", headers=_auth_header(role))
            assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_user_repository, None)
