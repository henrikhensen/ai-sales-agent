"""Integration tests for the Gmail/Outlook Draft Integration API.

Covers auth/role gating for the /integrations/email/* endpoints and the
/email-drafts/{id}/external-draft endpoints, plus regression checks for
health, CRM pipeline, do-not-contact, LLM settings, and the sales workflow.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_company_repository,
    get_contact_repository,
    get_do_not_contact_repository,
    get_email_draft_repository,
    get_email_provider_connection_repository,
    get_external_email_draft_repository,
    get_user_repository,
    get_workflow_run_repository,
)
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.enums import EmailDraftReviewStatus
from backend.main import app
from tests.conftest import (
    FakeCompanyRepository,
    FakeContactRepository,
    FakeDoNotContactRepository,
    FakeEmailDraftRepository,
    FakeEmailProviderConnectionRepository,
    FakeExternalEmailDraftRepository,
    FakeInteractionRepository,
    FakeLeadRepository,
    FakeUserRepository,
    FakeWorkflowRunRepository,
)

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
def fakes():
    repos = {
        get_company_repository: FakeCompanyRepository(),
        get_contact_repository: FakeContactRepository(),
        get_workflow_run_repository: FakeWorkflowRunRepository(),
        get_email_draft_repository: FakeEmailDraftRepository(),
        get_do_not_contact_repository: FakeDoNotContactRepository(),
        get_email_provider_connection_repository: FakeEmailProviderConnectionRepository(),
        get_external_email_draft_repository: FakeExternalEmailDraftRepository(),
    }
    for dependency, fake in repos.items():
        app.dependency_overrides[dependency] = _returning(fake)
    yield repos
    for dependency in repos:
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


async def _create_draft(fakes, **overrides) -> EmailDraft:
    defaults = dict(
        company_id=uuid.uuid4(),
        email_body="Hallo,\n\nGrüße",
        review_status=EmailDraftReviewStatus.APPROVED,
    )
    defaults.update(overrides)
    return await fakes[get_email_draft_repository].create(EmailDraft(**defaults))


# -- GET /integrations/email/status ---------------------------------------------

def test_status_without_token_returns_401():
    response = client.get("/api/v1/integrations/email/status")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_status_allowed_for_every_role(role):
    response = client.get(
        "/api/v1/integrations/email/status", headers=_auth_header(role)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active_provider"] == "mock"
    assert data["safe_mode"] is True


# -- GET /integrations/email/providers -------------------------------------------

def test_providers_without_token_returns_401():
    response = client.get("/api/v1/integrations/email/providers")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_providers_allowed_for_every_role(role):
    response = client.get(
        "/api/v1/integrations/email/providers", headers=_auth_header(role)
    )
    assert response.status_code == 200
    names = {item["provider"] for item in response.json()["items"]}
    assert names == {"mock", "gmail", "outlook"}


# -- POST /integrations/email/{provider}/connect/start ---------------------------

def test_connect_start_without_token_returns_401():
    response = client.post("/api/v1/integrations/email/mock/connect/start")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales"])
def test_connect_start_allowed_for_admin_and_sales(role):
    response = client.post(
        "/api/v1/integrations/email/mock/connect/start",
        headers=_auth_header(role),
    )
    assert response.status_code == 200
    assert response.json()["provider"] == "mock"


def test_connect_start_blocked_for_reviewer():
    response = client.post(
        "/api/v1/integrations/email/mock/connect/start",
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


# -- POST /integrations/email/disconnect -----------------------------------------

def test_disconnect_requires_auth():
    response = client.post("/api/v1/integrations/email/disconnect?provider=mock")
    assert response.status_code == 401


def test_disconnect_allowed_for_sales():
    response = client.post(
        "/api/v1/integrations/email/disconnect?provider=mock",
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "disconnected"


# -- POST /email-drafts/{draft_id}/external-draft --------------------------------

async def test_create_external_draft_without_token_returns_401():
    response = client.post(
        f"/api/v1/email-drafts/{uuid.uuid4()}/external-draft"
    )
    assert response.status_code == 401


async def test_create_external_draft_allowed_for_sales(fakes):
    draft = await _create_draft(fakes)
    response = client.post(
        f"/api/v1/email-drafts/{draft.id}/external-draft",
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["blocked"] is False
    assert data["external_draft"]["provider_status"] == "mock_created"
    assert data["external_draft"]["provider_status"] != "sent"


async def test_create_external_draft_blocked_for_reviewer(fakes):
    draft = await _create_draft(fakes)
    response = client.post(
        f"/api/v1/email-drafts/{draft.id}/external-draft",
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


async def test_create_external_draft_returns_404_for_unknown_draft():
    response = client.post(
        f"/api/v1/email-drafts/{uuid.uuid4()}/external-draft",
        headers=_auth_header("admin"),
    )
    assert response.status_code == 404


async def test_create_external_draft_blocked_when_not_approved(fakes):
    draft = await _create_draft(
        fakes, review_status=EmailDraftReviewStatus.NEEDS_REVIEW
    )
    response = client.post(
        f"/api/v1/email-drafts/{draft.id}/external-draft",
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["blocked"] is True
    assert data["block_reason"] == "review_not_approved"


async def test_create_external_draft_blocked_by_do_not_contact(fakes):
    from backend.domain.entities.company import Company

    company = await fakes[get_company_repository].create(
        Company(name="Blocked GmbH", domain="blocked.example")
    )
    draft = await _create_draft(fakes, company_id=company.id)

    create_response = client.post(
        "/api/v1/compliance/do-not-contact",
        json={"company_name": "Blocked GmbH", "reason": "Opt-out"},
        headers=_auth_header("admin"),
    )
    assert create_response.status_code == 201

    response = client.post(
        f"/api/v1/email-drafts/{draft.id}/external-draft",
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["blocked"] is True
    assert data["block_reason"] == "do_not_contact"


# -- GET /email-drafts/{draft_id}/external-draft ---------------------------------

async def test_get_external_draft_status_without_token_returns_401():
    response = client.get(f"/api/v1/email-drafts/{uuid.uuid4()}/external-draft")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
async def test_get_external_draft_status_allowed_for_every_role(fakes, role):
    draft = await _create_draft(fakes)
    response = client.get(
        f"/api/v1/email-drafts/{draft.id}/external-draft",
        headers=_auth_header(role),
    )
    assert response.status_code == 200
    assert response.json()["exists"] is False


# -- No send endpoints ------------------------------------------------------------

def test_no_send_endpoint_exists_anywhere():
    paths = [route.path for route in app.routes]
    assert not any("send" in path.lower() for path in paths)


# -- Regression -----------------------------------------------------------------

def test_health_endpoint_still_works():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_crm_pipeline_do_not_contact_and_llm_settings_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/crm/pipeline" in paths
    assert "/api/v1/compliance/do-not-contact" in paths
    assert "/api/v1/settings/llm/status" in paths
    assert "/api/v1/workflows/sales" in paths
    assert "/api/v1/integrations/email/status" in paths


async def test_sales_workflow_does_not_automatically_create_an_external_draft(fakes):
    from backend.api.v1.dependencies import get_lead_repository, get_interaction_repository

    app.dependency_overrides[get_lead_repository] = _returning(FakeLeadRepository())
    app.dependency_overrides[get_interaction_repository] = _returning(
        FakeInteractionRepository()
    )
    try:
        post_response = client.post(
            "/api/v1/workflows/sales",
            json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
            headers=_auth_header("admin"),
        )
        assert post_response.status_code == 200
        draft_id = post_response.json()["crm_email_draft_id"]
        assert draft_id is not None

        status_response = client.get(
            f"/api/v1/email-drafts/{draft_id}/external-draft",
            headers=_auth_header("admin"),
        )
        assert status_response.status_code == 200
        assert status_response.json()["exists"] is False
    finally:
        app.dependency_overrides.pop(get_lead_repository, None)
        app.dependency_overrides.pop(get_interaction_repository, None)
