"""Tests for GET /api/v1/system/status and GET /api/v1/system/backups/status.

Both are admin-only and must never leak a secret, API key, or token — only
which mode (mock/safe vs. real) each integration is running in.
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


def test_system_status_without_token_returns_401():
    response = client.get("/api/v1/system/status")
    assert response.status_code == 401


def test_system_status_blocked_for_non_admin():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    try:
        for role in ("sales", "reviewer"):
            response = client.get("/api/v1/system/status", headers=_auth_header(role))
            assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_user_repository, None)


def test_system_status_allowed_for_admin_and_reports_safe_modes():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    try:
        response = client.get("/api/v1/system/status", headers=_auth_header("admin"))
        assert response.status_code == 200
        data = response.json()

        # Mock stays the default for every integration.
        assert data["llm_provider"] == "mock"
        assert data["llm_real_calls_enabled"] is False
        assert data["email_integration_provider"] == "mock"
        assert data["email_real_drafts_enabled"] is False
        assert data["reply_tracking_provider"] == "mock"
        assert data["reply_real_reads_enabled"] is False

        assert data["database_status"] in ("up", "down")
        assert data["redis_status"] in ("up", "down")
        assert isinstance(data["production_warnings"], list)

        body = response.text
        for secret_like in _SECRET_LIKE_VALUES:
            assert secret_like not in body
    finally:
        app.dependency_overrides.pop(get_user_repository, None)


def test_backup_status_without_token_returns_401():
    response = client.get("/api/v1/system/backups/status")
    assert response.status_code == 401


def test_backup_status_blocked_for_non_admin():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    try:
        response = client.get(
            "/api/v1/system/backups/status", headers=_auth_header("sales")
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_user_repository, None)


def test_backup_status_allowed_for_admin_and_disabled_by_default():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    try:
        response = client.get(
            "/api/v1/system/backups/status", headers=_auth_header("admin")
        )
        assert response.status_code == 200
        data = response.json()
        assert data["backups_enabled"] is False
        assert "backup_dir" in data
        assert "retention_days" in data
        # No download link anywhere in the response.
        assert "download" not in response.text.lower()
    finally:
        app.dependency_overrides.pop(get_user_repository, None)


def test_no_backup_download_endpoint_exists():
    paths = [route.path for route in app.routes]
    assert not any("download" in path.lower() for path in paths)
