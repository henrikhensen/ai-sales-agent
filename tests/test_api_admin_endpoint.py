"""Integration tests for the Admin Controls API.

Covers auth/role gating (admin-only throughout — sales and reviewer are
both rejected), workspace settings load/update, the safety-critical
validation on Admin Controls updates, the setup checklist, and the
standing regression check that no secret is ever returned.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_icp_profile_repository,
    get_offer_profile_repository,
    get_user_repository,
    get_workspace_settings_repository,
)
from backend.main import app
from tests.conftest import (
    FakeICPProfileRepository,
    FakeOfferProfileRepository,
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


def test_workspace_settings_ohne_token_gibt_401():
    response = client.get("/api/v1/admin/workspace-settings")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["sales", "reviewer"])
def test_workspace_settings_verboten_fuer_nicht_admin(role):
    response = client.get("/api/v1/admin/workspace-settings", headers=_auth_header(role))
    assert response.status_code == 403


def test_workspace_settings_koennen_von_admin_geladen_werden():
    response = client.get("/api/v1/admin/workspace-settings", headers=_auth_header("admin"))
    assert response.status_code == 200
    assert response.json()["workspace_name"]


def test_workspace_settings_koennen_von_admin_geaendert_werden():
    response = client.patch(
        "/api/v1/admin/workspace-settings",
        json={"workspace_name": "New Name GmbH"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    assert response.json()["workspace_name"] == "New Name GmbH"


@pytest.mark.parametrize("role", ["sales", "reviewer"])
def test_sales_und_reviewer_duerfen_workspace_settings_nicht_aendern(role):
    response = client.patch(
        "/api/v1/admin/workspace-settings",
        json={"workspace_name": "Hijacked"},
        headers=_auth_header(role),
    )
    assert response.status_code == 403


def test_admin_controls_koennen_geladen_werden():
    response = client.get("/api/v1/admin/controls", headers=_auth_header("admin"))
    assert response.status_code == 200
    body = response.json()
    assert body["require_human_review"] is True
    assert body["require_do_not_contact_check"] is True


def test_admin_controls_blockieren_unsichere_aenderung():
    response = client.patch(
        "/api/v1/admin/controls",
        json={"require_human_review": False},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 400
    follow_up = client.get("/api/v1/admin/controls", headers=_auth_header("admin"))
    assert follow_up.json()["require_human_review"] is True


def test_allow_real_dispatch_wird_ohne_safety_nicht_erlaubt(monkeypatch):
    from backend.shared.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "outreach_dispatch_enable_real_send", False)
    response = client.patch(
        "/api/v1/admin/controls",
        json={"allow_real_dispatch": True},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 400


def test_dispatch_mode_manual_send_ohne_env_aktivierung_verboten(monkeypatch):
    from backend.shared.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "outreach_dispatch_enable_real_send", False)
    response = client.patch(
        "/api/v1/admin/controls",
        json={"dispatch_mode": "manual_send"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 400


def test_setup_checklist_funktioniert():
    response = client.get("/api/v1/admin/setup-checklist", headers=_auth_header("admin"))
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 10
    assert body["overall_status"] in ("passed", "warning", "blocker", "not_checked")


def test_api_zeigt_keine_secrets():
    response = client.get("/api/v1/admin/controls", headers=_auth_header("admin"))
    body_text = response.text.lower()
    for forbidden in ("token", "secret", "api_key", "client_secret", "password"):
        assert forbidden not in body_text


# -- regression: no send capability ------------------------------------------------


def test_kein_send_endpoint_unter_admin():
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/admin"):
            assert "send" not in path.lower()
