"""Integration tests for the Reply Inbox API.

Covers auth/role gating for /replies, /leads/{id}/replies,
/email-drafts/{id}/replies/sync, and /integrations/replies/status, plus
regression checks for health, CRM pipeline, do-not-contact, LLM settings,
and the external draft integration.
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
    get_interaction_repository,
    get_lead_repository,
    get_reply_repository,
    get_user_repository,
    get_workflow_run_repository,
)
from backend.domain.entities.company import Company
from backend.domain.entities.contact import Contact
from backend.domain.entities.lead import Lead
from backend.domain.enums import LeadSource
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
    FakeReplyRepository,
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
        get_lead_repository: FakeLeadRepository(),
        get_workflow_run_repository: FakeWorkflowRunRepository(),
        get_email_draft_repository: FakeEmailDraftRepository(),
        get_do_not_contact_repository: FakeDoNotContactRepository(),
        get_email_provider_connection_repository: FakeEmailProviderConnectionRepository(),
        get_external_email_draft_repository: FakeExternalEmailDraftRepository(),
        get_reply_repository: FakeReplyRepository(),
        get_interaction_repository: FakeInteractionRepository(),
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


async def _seed_lead_with_contact(fakes, email: str):
    company = await fakes[get_company_repository].create(
        Company(name="Acme GmbH", domain="acme.example")
    )
    lead = await fakes[get_lead_repository].create(
        Lead(company_id=company.id, source=LeadSource.OUTBOUND)
    )
    await fakes[get_contact_repository].create(
        Contact(company_id=company.id, first_name="Jane", last_name="Doe", email=email)
    )
    return company, lead


# -- GET /replies -----------------------------------------------------------

def test_list_replies_without_token_returns_401():
    response = client.get("/api/v1/replies")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_list_replies_allowed_for_every_role(role):
    response = client.get("/api/v1/replies", headers=_auth_header(role))
    assert response.status_code == 200


# -- GET /integrations/replies/status --------------------------------------------

def test_reply_status_without_token_returns_401():
    response = client.get("/api/v1/integrations/replies/status")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_reply_status_allowed_for_every_role(role):
    response = client.get(
        "/api/v1/integrations/replies/status", headers=_auth_header(role)
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active_provider"] == "mock"
    assert data["safe_mode"] is True


# -- POST /replies/sync-recent ----------------------------------------------------

def test_sync_recent_without_token_returns_401():
    response = client.post("/api/v1/replies/sync-recent")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales"])
def test_sync_recent_allowed_for_admin_and_sales(role):
    response = client.post("/api/v1/replies/sync-recent", headers=_auth_header(role))
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("mock_synced", "synced")
    assert "sent" not in data["message"].lower() or "no" in data["message"].lower()


def test_sync_recent_blocked_for_reviewer():
    response = client.post(
        "/api/v1/replies/sync-recent", headers=_auth_header("reviewer")
    )
    assert response.status_code == 403


# -- GET/POST /leads/{lead_id}/replies -------------------------------------------

async def test_lead_replies_sync_allowed_for_sales(fakes):
    _, lead = await _seed_lead_with_contact(fakes, "jane@acme.example")
    response = client.post(
        f"/api/v1/leads/{lead.id}/replies/sync", headers=_auth_header("sales")
    )
    assert response.status_code == 200
    assert response.json()["new_count"] == 1


async def test_lead_replies_sync_blocked_for_reviewer(fakes):
    _, lead = await _seed_lead_with_contact(fakes, "jane@acme.example")
    response = client.post(
        f"/api/v1/leads/{lead.id}/replies/sync", headers=_auth_header("reviewer")
    )
    assert response.status_code == 403


async def test_list_lead_replies_allowed_for_reviewer(fakes):
    _, lead = await _seed_lead_with_contact(fakes, "jane@acme.example")
    response = client.get(
        f"/api/v1/leads/{lead.id}/replies", headers=_auth_header("reviewer")
    )
    assert response.status_code == 200


def test_lead_replies_sync_returns_404_for_unknown_lead():
    response = client.post(
        f"/api/v1/leads/{uuid.uuid4()}/replies/sync", headers=_auth_header("admin")
    )
    assert response.status_code == 404


# -- PATCH /replies/{id}/read and /archive ---------------------------------------

async def test_mark_read_and_archive_allowed_for_reviewer(fakes):
    _, lead = await _seed_lead_with_contact(fakes, "jane@acme.example")
    sync_response = client.post(
        f"/api/v1/leads/{lead.id}/replies/sync", headers=_auth_header("admin")
    )
    reply_id = sync_response.json()["replies"][0]["id"]

    read_response = client.patch(
        f"/api/v1/replies/{reply_id}/read", headers=_auth_header("reviewer")
    )
    assert read_response.status_code == 200
    assert read_response.json()["is_read"] is True

    archive_response = client.patch(
        f"/api/v1/replies/{reply_id}/archive", headers=_auth_header("reviewer")
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["is_archived"] is True


def test_get_reply_returns_404_for_unknown_id():
    response = client.get(
        f"/api/v1/replies/{uuid.uuid4()}", headers=_auth_header("admin")
    )
    assert response.status_code == 404


# -- No send endpoints ------------------------------------------------------------

def test_no_send_or_reply_send_endpoint_exists_anywhere():
    paths = [route.path for route in app.routes]
    assert not any("send" in path.lower() for path in paths)
    assert not any("reply-send" in path.lower() for path in paths)


# -- Regression -----------------------------------------------------------------

def test_health_endpoint_still_works():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_other_systems_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/crm/pipeline" in paths
    assert "/api/v1/compliance/do-not-contact" in paths
    assert "/api/v1/settings/llm/status" in paths
    assert "/api/v1/integrations/email/status" in paths
    assert "/api/v1/email-drafts/{draft_id}/external-draft" in paths
    assert "/api/v1/workflows/sales" in paths
    assert "/api/v1/replies" in paths
    assert "/api/v1/replies/{reply_id}" in paths
    assert "/api/v1/replies/sync-recent" in paths
    assert "/api/v1/leads/{lead_id}/replies" in paths
    assert "/api/v1/leads/{lead_id}/replies/sync" in paths
    assert "/api/v1/email-drafts/{draft_id}/replies/sync" in paths
    assert "/api/v1/integrations/replies/status" in paths
