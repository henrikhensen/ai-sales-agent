"""Integration tests for the LLM provider settings API.

Covers auth/role gating (GET status: all three roles; POST test: admin
only), that no response ever contains ANTHROPIC_API_KEY, and regression
checks that health, auth, agents, and the sales workflow keep working now
that the settings router is wired into the app.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_llm_provider,
    get_llm_settings_service,
    get_user_repository,
)
from backend.application.settings.llm_settings_service import LLMSettingsService
from backend.infrastructure.llm.mock_provider import MockLLMProvider
from backend.main import app
from backend.shared.config import Settings
from tests.conftest import FakeUserRepository

client = TestClient(app)

_REAL_LOOKING_KEY = "sk-ant-super-secret-value-should-never-leak"


def _returning(fake):
    def _get():
        return fake

    return _get


def _settings(**overrides) -> Settings:
    # Settings fields declare an explicit env-var alias (e.g. LLM_PROVIDER)
    # and pydantic only accepts that alias as a constructor keyword by
    # default (not the snake_case Python attribute name).
    defaults: dict = dict(
        LLM_PROVIDER="mock",
        ANTHROPIC_API_KEY=None,
        ANTHROPIC_MODEL="claude-opus-4-8",
        LLM_MAX_TOKENS=1024,
        LLM_ENABLE_REAL_CALLS=False,
        LLM_TIMEOUT_SECONDS=30,
    )
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture(autouse=True)
def _fake_user_repository():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    yield fake_repo
    app.dependency_overrides.pop(get_user_repository, None)


@pytest.fixture(autouse=True)
def _mock_llm_setup():
    """Deterministic mock-mode LLM config, independent of ambient .env."""
    app.dependency_overrides[get_llm_provider] = _returning(MockLLMProvider())
    app.dependency_overrides[get_llm_settings_service] = _returning(
        LLMSettingsService(_settings())
    )
    yield
    app.dependency_overrides.pop(get_llm_provider, None)
    app.dependency_overrides.pop(get_llm_settings_service, None)


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


# -- GET /settings/llm/status -------------------------------------------------

def test_llm_status_without_token_returns_401():
    response = client.get("/api/v1/settings/llm/status")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "reviewer", "sales"])
def test_llm_status_allowed_for_every_role(role):
    response = client.get("/api/v1/settings/llm/status", headers=_auth_header(role))
    assert response.status_code == 200


def test_llm_status_reports_mock_mode_by_default():
    response = client.get("/api/v1/settings/llm/status", headers=_auth_header("admin"))
    data = response.json()

    assert data["active_provider"] == "mock"
    assert data["mock_mode"] is True
    assert data["safe_mode"] is True
    assert data["real_calls_enabled"] is False
    assert data["anthropic_configured"] is False


def test_llm_status_never_returns_the_api_key():
    app.dependency_overrides[get_llm_settings_service] = _returning(
        LLMSettingsService(
            _settings(LLM_PROVIDER="anthropic", ANTHROPIC_API_KEY=_REAL_LOOKING_KEY)
        )
    )
    try:
        response = client.get(
            "/api/v1/settings/llm/status", headers=_auth_header("admin")
        )
    finally:
        app.dependency_overrides[get_llm_settings_service] = _returning(
            LLMSettingsService(_settings())
        )

    assert response.status_code == 200
    data = response.json()
    assert data["anthropic_configured"] is True
    assert "anthropic_api_key" not in data
    assert _REAL_LOOKING_KEY not in response.text


# -- POST /settings/llm/test ---------------------------------------------------

def test_llm_test_without_token_returns_401():
    response = client.post("/api/v1/settings/llm/test")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["reviewer", "sales"])
def test_llm_test_requires_admin(role):
    response = client.post("/api/v1/settings/llm/test", headers=_auth_header(role))
    assert response.status_code == 403


def test_llm_test_as_admin_runs_mock_successfully():
    response = client.post("/api/v1/settings/llm/test", headers=_auth_header("admin"))

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "mock"
    assert data["ok"] is True


def test_llm_test_blocks_real_calls_when_disabled():
    app.dependency_overrides[get_llm_settings_service] = _returning(
        LLMSettingsService(
            _settings(
                LLM_PROVIDER="anthropic",
                ANTHROPIC_API_KEY=_REAL_LOOKING_KEY,
                LLM_ENABLE_REAL_CALLS=False,
            )
        )
    )
    try:
        response = client.post(
            "/api/v1/settings/llm/test", headers=_auth_header("admin")
        )
    finally:
        app.dependency_overrides[get_llm_settings_service] = _returning(
            LLMSettingsService(_settings())
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert data["message"] == (
        "Real LLM calls are disabled. Enable LLM_ENABLE_REAL_CALLS=true in "
        ".env to test Anthropic."
    )
    assert _REAL_LOOKING_KEY not in response.text


def test_llm_endpoints_registered_under_settings_tag():
    settings_routes = [
        route
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/v1/settings")
    ]
    paths = {route.path for route in settings_routes}
    assert "/api/v1/settings/llm/status" in paths
    assert "/api/v1/settings/llm/test" in paths
    for route in settings_routes:
        assert "settings" in getattr(route, "tags", [])


# -- Regression: existing endpoints keep working -------------------------------

def test_health_endpoint_still_works():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] in ("ok", "degraded")


def test_auth_endpoints_still_work():
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "settings-regression@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "settings-regression@example.com", "password": "testpassword123"},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"


def test_agent_endpoint_still_works():
    response = client.post(
        "/api/v1/agents/lead-research", json={"company_name": "Acme GmbH"}
    )
    assert response.status_code == 200
    assert response.json()["company_name"] == "Acme GmbH"


def test_sales_workflow_endpoint_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/workflows/sales" in paths
    assert "/api/v1/workflows/sales/runs" in paths
