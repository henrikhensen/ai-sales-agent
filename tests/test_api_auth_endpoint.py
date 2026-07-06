import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_company_repository,
    get_contact_repository,
    get_email_draft_repository,
    get_interaction_repository,
    get_lead_repository,
    get_review_event_repository,
    get_user_repository,
    get_workflow_run_repository,
)
from backend.main import app
from tests.conftest import (
    FakeCompanyRepository,
    FakeContactRepository,
    FakeEmailDraftRepository,
    FakeInteractionRepository,
    FakeLeadRepository,
    FakeReviewEventRepository,
    FakeUserRepository,
    FakeWorkflowRunRepository,
)

# No context manager → lifespan (and thus DB init) does not run. The user
# repository dependency is overridden below with an in-memory fake, so
# registration/login/me are exercised without a real database.
client = TestClient(app)


@pytest.fixture(autouse=True)
def fake_users():
    users = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = lambda: users
    yield users
    app.dependency_overrides.pop(get_user_repository, None)


def _register(**overrides):
    payload = {"email": "user@example.com", "password": "securepassword123"}
    payload.update(overrides)
    return client.post("/api/v1/auth/register", json=payload)


# -- POST /auth/register -----------------------------------------------------

def test_register_endpoint_creates_a_user():
    response = _register(full_name="Henrik", role="admin")

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["full_name"] == "Henrik"
    assert data["role"] == "admin"
    assert data["is_active"] is True
    assert data["is_superuser"] is False
    assert "hashed_password" not in data
    assert "password" not in data


def test_register_endpoint_rejects_duplicate_email():
    _register()
    response = _register()
    assert response.status_code == 409


def test_register_endpoint_rejects_short_password():
    response = _register(password="short")
    assert response.status_code == 422


def test_register_endpoint_rejects_invalid_email():
    response = _register(email="not-an-email")
    assert response.status_code == 422


def test_register_endpoint_defaults_role_to_sales():
    response = _register()
    assert response.json()["role"] == "sales"


# -- POST /auth/login ---------------------------------------------------------

def test_login_endpoint_returns_a_bearer_token():
    _register()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "securepassword123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str) and data["access_token"]


def test_login_endpoint_rejects_wrong_password():
    _register()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_login_endpoint_rejects_unknown_email():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "securepassword123"},
    )
    assert response.status_code == 401


# -- GET /auth/me ---------------------------------------------------------------

def test_me_endpoint_returns_current_user_with_valid_token():
    _register(full_name="Henrik")
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "securepassword123"},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["full_name"] == "Henrik"


def test_me_endpoint_without_token_returns_401():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_endpoint_with_garbage_token_returns_401():
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


# -- GET /users -----------------------------------------------------------------

def test_users_endpoint_requires_authentication():
    response = client.get("/api/v1/users")
    assert response.status_code == 401


def test_users_endpoint_requires_admin_role():
    _register(email="sales@example.com", role="sales")
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "sales@example.com", "password": "securepassword123"},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_users_endpoint_allows_admin_and_lists_users():
    _register(email="admin@example.com", role="admin")
    _register(email="sales@example.com", role="sales")
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "securepassword123"},
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2


# -- regression: existing public endpoints remain unprotected/reachable ------

def test_health_endpoint_still_registered_and_reachable():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_sales_workflow_endpoint_still_reachable_without_auth():
    overrides = {
        get_company_repository: lambda: FakeCompanyRepository(),
        get_lead_repository: lambda: FakeLeadRepository(),
        get_contact_repository: lambda: FakeContactRepository(),
        get_interaction_repository: lambda: FakeInteractionRepository(),
        get_email_draft_repository: lambda: FakeEmailDraftRepository(),
        get_workflow_run_repository: lambda: FakeWorkflowRunRepository(),
    }
    for dependency, fake in overrides.items():
        app.dependency_overrides[dependency] = fake
    try:
        response = client.post(
            "/api/v1/workflows/sales",
            json={
                "company_name": "Acme GmbH",
                "product_or_service_offered": "Freight API",
            },
        )
    finally:
        for dependency in overrides:
            app.dependency_overrides.pop(dependency, None)

    assert response.status_code == 200


def test_review_endpoints_still_registered_and_do_not_require_auth():
    paths = {route.path for route in app.routes}
    assert "/api/v1/reviews/email-drafts/{email_draft_id}/status" in paths
    assert "/api/v1/reviews/workflows/{workflow_id}/comment" in paths

    overrides = {
        get_email_draft_repository: lambda: FakeEmailDraftRepository(),
        get_workflow_run_repository: lambda: FakeWorkflowRunRepository(),
        get_review_event_repository: lambda: FakeReviewEventRepository(),
    }
    for dependency, fake in overrides.items():
        app.dependency_overrides[dependency] = fake
    try:
        response = client.post(
            "/api/v1/reviews/workflows/00000000-0000-0000-0000-000000000000/comment",
            json={"comment": "Bitte pruefen."},
        )
    finally:
        for dependency in overrides:
            app.dependency_overrides.pop(dependency, None)

    # 404 (unknown workflow) proves the request reached the handler without
    # being rejected for missing auth — reviews stay unprotected this phase.
    assert response.status_code == 404


def test_frontend_relevant_public_endpoints_remain_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/companies" in paths
    assert "/api/v1/leads" in paths
    assert "/api/v1/contacts" in paths
    assert "/api/v1/interactions" in paths
    assert "/api/v1/email-drafts" in paths
    assert "/api/v1/workflows/sales/runs" in paths
    assert "/api/v1/workflows/sales/runs/{workflow_id}/crm-links" in paths


def test_auth_endpoints_are_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/users" in paths
