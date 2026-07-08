"""Integration tests for the Customer Onboarding API.

Covers auth/role gating (view own status: all roles; complete/skip: sales
and admin only, not reviewer), a full step-complete/skip/complete-all
flow through the real HTTP stack, the readiness endpoint, and the
standing regression checks (no secrets, no send-capable endpoint).
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_icp_profile_repository,
    get_offer_profile_repository,
    get_onboarding_status_repository,
    get_user_repository,
    get_workspace_settings_repository,
)
from backend.main import app
from tests.conftest import (
    FakeICPProfileRepository,
    FakeOfferProfileRepository,
    FakeOnboardingStatusRepository,
    FakeUserRepository,
    FakeWorkspaceSettingsRepository,
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
        get_icp_profile_repository: FakeICPProfileRepository(),
        get_offer_profile_repository: FakeOfferProfileRepository(),
        get_onboarding_status_repository: FakeOnboardingStatusRepository(),
        get_workspace_settings_repository: FakeWorkspaceSettingsRepository(),
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


def test_status_ohne_token_gibt_401():
    response = client.get("/api/v1/onboarding/status")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_status_erlaubt_fuer_jede_rolle(role):
    response = client.get("/api/v1/onboarding/status", headers=_auth_header(role))
    assert response.status_code == 200
    body = response.json()
    assert body["current_step"] == "welcome"
    assert body["progress_percent"] == 0


def test_complete_step_verboten_fuer_reviewer():
    response = client.patch(
        "/api/v1/onboarding/steps/welcome/complete",
        json={},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_skip_step_verboten_fuer_reviewer():
    response = client.patch(
        "/api/v1/onboarding/steps/welcome/skip",
        json={},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_complete_step_erlaubt_fuer_sales():
    response = client.patch(
        "/api/v1/onboarding/steps/welcome/complete",
        json={},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200
    body = response.json()
    assert "welcome" in body["status"]["completed_steps"]
    assert body["status"]["current_step"] == "profile_setup"


def test_unbekannter_step_gibt_400():
    response = client.patch(
        "/api/v1/onboarding/steps/not_a_step/complete",
        json={},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 400


def test_onboarding_complete_end_to_end():
    header = _auth_header("admin")
    response = client.post("/api/v1/onboarding/complete", headers=header)
    assert response.status_code == 200
    assert response.json()["status"]["is_completed"] is True


def test_readiness_endpoint_funktioniert():
    response = client.get("/api/v1/onboarding/readiness", headers=_auth_header("sales"))
    assert response.status_code == 200
    body = response.json()
    assert body["readiness_level"] in (
        "not_ready",
        "demo_ready",
        "internal_ready",
        "beta_ready",
    )
    assert "checks" in body


def test_readiness_zeigt_keine_secrets():
    response = client.get("/api/v1/onboarding/readiness", headers=_auth_header("admin"))
    body_text = response.text.lower()
    for forbidden in ("token", "secret", "api_key", "password"):
        assert forbidden not in body_text


# -- regression: no send capability ------------------------------------------------


def test_kein_send_endpoint_unter_onboarding():
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/onboarding"):
            assert "send" not in path.lower()
            assert "batch" not in path.lower()
