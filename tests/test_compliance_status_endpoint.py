"""Tests for GET /api/v1/compliance/status.

Covers role gating and the hard-coded safety invariants:
email_sending_enabled and automatic_contact_enabled must always be False,
since there is no send/auto-contact capability anywhere in this system.
"""

import uuid

from fastapi.testclient import TestClient

from backend.api.v1.dependencies import get_user_repository
from backend.main import app
from tests.conftest import FakeUserRepository

client = TestClient(app)

_SECRET_LIKE_VALUES = (
    "dev-only-insecure-secret-change-me",
    "sales_agent_password",
    "ANTHROPIC_API_KEY",
    "GOOGLE_CLIENT_SECRET",
    "MICROSOFT_CLIENT_SECRET",
)


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


def test_compliance_status_without_token_returns_401():
    response = client.get("/api/v1/compliance/status")
    assert response.status_code == 401


def test_compliance_status_allowed_for_admin_sales_and_reviewer():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    try:
        for role in ("admin", "sales", "reviewer"):
            response = client.get(
                "/api/v1/compliance/status", headers=_auth_header(role)
            )
            assert response.status_code == 200
    finally:
        app.dependency_overrides.pop(get_user_repository, None)


def test_compliance_status_email_sending_and_automatic_contact_are_false():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    try:
        response = client.get("/api/v1/compliance/status", headers=_auth_header("admin"))
        data = response.json()
        assert data["email_sending_enabled"] is False
        assert data["automatic_contact_enabled"] is False
        assert data["do_not_contact_enabled"] is True
        assert data["human_review_enabled"] is True
    finally:
        app.dependency_overrides.pop(get_user_repository, None)


def test_compliance_status_reports_mock_safe_mode_by_default():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    try:
        response = client.get("/api/v1/compliance/status", headers=_auth_header("admin"))
        data = response.json()
        assert data["llm_provider"] == "mock"
        assert data["email_integration_provider"] == "mock"
        assert data["reply_tracking_provider"] == "mock"
        assert data["safe_mode"] is True
        assert "keine" not in data["message"].lower() or "gesendet" in data["message"].lower()
    finally:
        app.dependency_overrides.pop(get_user_repository, None)


def test_compliance_status_never_leaks_a_secret_like_value():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    try:
        response = client.get("/api/v1/compliance/status", headers=_auth_header("admin"))
        body = response.text
        for secret_like in _SECRET_LIKE_VALUES:
            assert secret_like not in body
    finally:
        app.dependency_overrides.pop(get_user_repository, None)
