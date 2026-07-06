"""Integration tests for the Do-not-contact compliance API.

Covers auth/role gating (GET/POST check: admin/sales/reviewer; POST create:
admin/sales; PATCH update/deactivate: admin only), plus regression checks
for health, the sales workflow, and CRM pipeline endpoints.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import get_do_not_contact_repository, get_user_repository
from backend.main import app
from tests.conftest import FakeDoNotContactRepository, FakeUserRepository

client = TestClient(app)


def _returning(fake):
    def _get():
        return fake

    return _get


@pytest.fixture(autouse=True)
def _fake_user_repository():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    yield fake_repo
    app.dependency_overrides.pop(get_user_repository, None)


@pytest.fixture(autouse=True)
def _fake_do_not_contact_repository():
    fake_repo = FakeDoNotContactRepository()
    app.dependency_overrides[get_do_not_contact_repository] = _returning(fake_repo)
    yield fake_repo
    app.dependency_overrides.pop(get_do_not_contact_repository, None)


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


# -- GET /compliance/do-not-contact --------------------------------------------

def test_list_without_token_returns_401():
    response = client.get("/api/v1/compliance/do-not-contact")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_list_allowed_for_every_role(role):
    response = client.get(
        "/api/v1/compliance/do-not-contact", headers=_auth_header(role)
    )
    assert response.status_code == 200


# -- POST /compliance/do-not-contact --------------------------------------------

def test_create_without_token_returns_401():
    response = client.post(
        "/api/v1/compliance/do-not-contact",
        json={"email": "user@example.com", "reason": "Opt-out"},
    )
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales"])
def test_create_allowed_for_admin_and_sales(role):
    response = client.post(
        "/api/v1/compliance/do-not-contact",
        json={"email": "user@example.com", "reason": "Opt-out"},
        headers=_auth_header(role),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["is_active"] is True


def test_create_blocked_for_reviewer():
    response = client.post(
        "/api/v1/compliance/do-not-contact",
        json={"email": "user@example.com", "reason": "Opt-out"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_create_rejects_missing_target():
    response = client.post(
        "/api/v1/compliance/do-not-contact",
        json={"reason": "No target given"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 422


def test_create_stores_email_lowercase():
    response = client.post(
        "/api/v1/compliance/do-not-contact",
        json={"email": "User@Example.COM", "reason": "Opt-out"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"


# -- PATCH /compliance/do-not-contact/{entry_id} --------------------------------

def _create_entry(**overrides) -> dict:
    payload = {"email": "user@example.com", "reason": "Opt-out"}
    payload.update(overrides)
    response = client.post(
        "/api/v1/compliance/do-not-contact",
        json=payload,
        headers=_auth_header("admin"),
    )
    assert response.status_code == 201
    return response.json()


def test_update_requires_admin():
    entry = _create_entry()
    response = client.patch(
        f"/api/v1/compliance/do-not-contact/{entry['id']}",
        json={"reason": "New reason"},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 403


def test_update_as_admin_changes_reason():
    entry = _create_entry()
    response = client.patch(
        f"/api/v1/compliance/do-not-contact/{entry['id']}",
        json={"reason": "Updated reason"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    assert response.json()["reason"] == "Updated reason"


def test_update_returns_404_for_unknown_entry():
    response = client.patch(
        f"/api/v1/compliance/do-not-contact/{uuid.uuid4()}",
        json={"reason": "New reason"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 404


# -- PATCH /compliance/do-not-contact/{entry_id}/deactivate ---------------------

def test_deactivate_requires_admin():
    entry = _create_entry()
    response = client.patch(
        f"/api/v1/compliance/do-not-contact/{entry['id']}/deactivate",
        headers=_auth_header("sales"),
    )
    assert response.status_code == 403


def test_deactivate_as_admin_sets_inactive():
    entry = _create_entry()
    response = client.patch(
        f"/api/v1/compliance/do-not-contact/{entry['id']}/deactivate",
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


# -- POST /compliance/do-not-contact/check --------------------------------------

def test_check_without_token_returns_401():
    response = client.post(
        "/api/v1/compliance/do-not-contact/check", json={"email": "user@example.com"}
    )
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_check_allowed_for_every_role(role):
    response = client.post(
        "/api/v1/compliance/do-not-contact/check",
        json={"email": "user@example.com"},
        headers=_auth_header(role),
    )
    assert response.status_code == 200


def test_check_rejects_missing_target():
    response = client.post(
        "/api/v1/compliance/do-not-contact/check",
        json={},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 422


def test_check_reports_blocked_after_create():
    _create_entry(email="blocked@example.com")
    response = client.post(
        "/api/v1/compliance/do-not-contact/check",
        json={"email": "blocked@example.com"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_blocked"] is True
    assert data["matched_by"] == "email"


def test_check_never_mentions_sending():
    _create_entry(email="blocked@example.com")
    response = client.post(
        "/api/v1/compliance/do-not-contact/check",
        json={"email": "blocked@example.com"},
        headers=_auth_header("admin"),
    )
    assert "sent" not in response.text.lower()


# -- Regression -----------------------------------------------------------------

def test_health_endpoint_still_works():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_sales_workflow_and_crm_pipeline_endpoints_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/workflows/sales" in paths
    assert "/api/v1/crm/pipeline" in paths
    assert "/api/v1/compliance/do-not-contact" in paths
    assert "/api/v1/compliance/do-not-contact/check" in paths
    assert "/api/v1/compliance/do-not-contact/{entry_id}/deactivate" in paths
