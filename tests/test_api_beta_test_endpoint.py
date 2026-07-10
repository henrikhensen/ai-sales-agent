"""Integration tests for the Beta Test Session API.

Covers auth/role gating (create/start/complete: admin/sales; view
sessions: admin/sales/reviewer; dashboard: admin-only), a full
create -> start -> complete flow through the real HTTP stack, and the
standing regression check that unauthenticated access is rejected and no
send-capable endpoint exists.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_beta_test_session_repository,
    get_quality_score_repository,
    get_user_feedback_repository,
    get_user_repository,
)
from backend.main import app
from tests.conftest import (
    FakeBetaTestSessionRepository,
    FakeQualityScoreRepository,
    FakeUserFeedbackRepository,
    FakeUserRepository,
)

client = TestClient(app)


def _returning(fake):
    def _get():
        return fake

    return _get


@pytest.fixture(autouse=True)
def _fake_repositories():
    overrides = {
        get_user_repository: FakeUserRepository(),
        get_quality_score_repository: FakeQualityScoreRepository(),
        get_user_feedback_repository: FakeUserFeedbackRepository(),
        get_beta_test_session_repository: FakeBetaTestSessionRepository(),
    }
    for dependency, fake in overrides.items():
        app.dependency_overrides[dependency] = _returning(fake)
    yield overrides
    for dependency in overrides:
        app.dependency_overrides.pop(dependency, None)


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


def test_create_session_requires_auth():
    response = client.post("/api/v1/beta-test/sessions", json={"name": "Round 1"})
    assert response.status_code == 401


def test_reviewer_cannot_create_session():
    response = client.post(
        "/api/v1/beta-test/sessions",
        json={"name": "Round 1"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_reviewer_can_view_sessions():
    client.post(
        "/api/v1/beta-test/sessions",
        json={"name": "Round 1"},
        headers=_auth_header("admin"),
    )
    response = client.get("/api/v1/beta-test/sessions", headers=_auth_header("reviewer"))
    assert response.status_code == 200


def test_sales_can_create_start_and_complete_session():
    created = client.post(
        "/api/v1/beta-test/sessions",
        json={"name": "Round 1", "target_goal": "Validate email drafts"},
        headers=_auth_header("sales"),
    )
    assert created.status_code == 201
    session_id = created.json()["id"]
    assert created.json()["status"] == "planned"

    started = client.patch(
        f"/api/v1/beta-test/sessions/{session_id}/start",
        headers=_auth_header("sales"),
    )
    assert started.status_code == 200
    assert started.json()["status"] == "running"

    completed = client.patch(
        f"/api/v1/beta-test/sessions/{session_id}/complete",
        headers=_auth_header("sales"),
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"


def test_starting_a_running_session_returns_400():
    created = client.post(
        "/api/v1/beta-test/sessions",
        json={"name": "Round 1"},
        headers=_auth_header("admin"),
    ).json()
    client.patch(
        f"/api/v1/beta-test/sessions/{created['id']}/start",
        headers=_auth_header("admin"),
    )
    second_start = client.patch(
        f"/api/v1/beta-test/sessions/{created['id']}/start",
        headers=_auth_header("admin"),
    )
    assert second_start.status_code == 400


def test_get_session_not_found_returns_404():
    response = client.get(
        f"/api/v1/beta-test/sessions/{uuid.uuid4()}", headers=_auth_header("admin")
    )
    assert response.status_code == 404


def test_dashboard_is_admin_only():
    sales_response = client.get(
        "/api/v1/beta-test/dashboard", headers=_auth_header("sales")
    )
    assert sales_response.status_code == 403

    admin_response = client.get(
        "/api/v1/beta-test/dashboard", headers=_auth_header("admin")
    )
    assert admin_response.status_code == 200
    assert "readiness_level" in admin_response.json()


def test_no_send_capable_endpoint_exists_under_beta_test():
    openapi = client.get("/openapi.json").json()
    for path in openapi["paths"]:
        if path.startswith("/api/v1/beta-test"):
            assert "send" not in path.lower()
