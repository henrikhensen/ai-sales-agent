"""Integration tests verifying audit log entries are actually created by
key actions (login, sales workflow, do-not-contact block, review approval,
external draft creation, reply sync), that entries never leak secrets, and
that the GET /api/v1/audit-logs endpoints are admin-only.

Audit logging is disabled by default across the test suite (see
``_test_safety_defaults`` in tests/conftest.py, which avoids a real DB
connection). Each test here explicitly re-enables it and overrides the
audit log repository with an in-memory fake.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_audit_log_repository,
    get_company_repository,
    get_contact_repository,
    get_do_not_contact_repository,
    get_email_draft_repository,
    get_email_provider_connection_repository,
    get_external_email_draft_repository,
    get_interaction_repository,
    get_lead_repository,
    get_quality_score_repository,
    get_reply_repository,
    get_review_event_repository,
    get_user_feedback_repository,
    get_user_repository,
    get_workflow_run_repository,
)
from backend.domain.entities.company import Company
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.entities.lead import Lead
from backend.domain.enums import EmailDraftReviewStatus, LeadSource
from backend.main import app
from backend.shared.config import get_settings
from tests.conftest import (
    FakeAuditLogRepository,
    FakeCompanyRepository,
    FakeContactRepository,
    FakeDoNotContactRepository,
    FakeEmailDraftRepository,
    FakeEmailProviderConnectionRepository,
    FakeExternalEmailDraftRepository,
    FakeInteractionRepository,
    FakeLeadRepository,
    FakeQualityScoreRepository,
    FakeReplyRepository,
    FakeReviewEventRepository,
    FakeUserFeedbackRepository,
    FakeUserRepository,
    FakeWorkflowRunRepository,
)

client = TestClient(app)

_SECRET_LIKE_VALUES = (
    "dev-only-insecure-secret-change-me",
    "sales_agent_password",
    "ANTHROPIC_API_KEY",
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


@pytest.fixture
def audit_repo(monkeypatch):
    """Enable audit logging (disabled by default in tests) and back it with
    an in-memory fake so no real database is touched."""
    settings = get_settings()
    monkeypatch.setattr(settings, "audit_logs_enabled", True)
    repo = FakeAuditLogRepository()
    app.dependency_overrides[get_audit_log_repository] = _returning(repo)
    yield repo
    app.dependency_overrides.pop(get_audit_log_repository, None)


@pytest.fixture(autouse=True)
def _fake_user_repository():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    yield fake_repo
    app.dependency_overrides.pop(get_user_repository, None)


@pytest.fixture
def crm_fakes():
    repos = {
        get_company_repository: FakeCompanyRepository(),
        get_contact_repository: FakeContactRepository(),
        get_lead_repository: FakeLeadRepository(),
        get_workflow_run_repository: FakeWorkflowRunRepository(),
        get_email_draft_repository: FakeEmailDraftRepository(),
        get_do_not_contact_repository: FakeDoNotContactRepository(),
        get_interaction_repository: FakeInteractionRepository(),
        get_review_event_repository: FakeReviewEventRepository(),
        get_email_provider_connection_repository: FakeEmailProviderConnectionRepository(),
        get_external_email_draft_repository: FakeExternalEmailDraftRepository(),
        get_reply_repository: FakeReplyRepository(),
        get_quality_score_repository: FakeQualityScoreRepository(),
        get_user_feedback_repository: FakeUserFeedbackRepository(),
    }
    for dep, fake in repos.items():
        app.dependency_overrides[dep] = _returning(fake)
    yield repos
    for dep in repos:
        app.dependency_overrides.pop(dep, None)


# -- login --------------------------------------------------------------------


async def test_audit_log_created_on_login(audit_repo):
    email = f"audit-{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpassword123"},
    )
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "testpassword123"}
    )
    assert response.status_code == 200

    entries = await audit_repo.list_filtered(action="login")
    assert any(e.result == "success" for e in entries)


async def test_audit_log_created_on_failed_login(audit_repo):
    email = f"audit-{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpassword123"},
    )
    client.post(
        "/api/v1/auth/login", json={"email": email, "password": "wrong-password"}
    )

    entries = await audit_repo.list_filtered(action="login", result="failed")
    assert len(entries) == 1


# -- sales workflow -------------------------------------------------------------


async def test_audit_log_created_on_sales_workflow(audit_repo, crm_fakes):
    response = client.post(
        "/api/v1/workflows/sales",
        json={
            "company_name": "AuditTestCo",
            "product_or_service_offered": "Testing",
        },
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200

    started = await audit_repo.list_filtered(action="sales_workflow_started")
    completed = await audit_repo.list_filtered(action="sales_workflow_completed")
    assert len(started) == 1
    assert len(completed) == 1


# -- do-not-contact block ------------------------------------------------------


async def test_audit_log_created_on_do_not_contact_check_blocked(audit_repo, crm_fakes):
    admin_header = _auth_header("admin")
    client.post(
        "/api/v1/compliance/do-not-contact",
        json={"email": "blocked@example.com", "reason": "test", "source": "manual"},
        headers=admin_header,
    )
    response = client.post(
        "/api/v1/compliance/do-not-contact/check",
        json={"email": "blocked@example.com"},
        headers=admin_header,
    )
    assert response.json()["is_blocked"] is True

    entries = await audit_repo.list_filtered(action="do_not_contact_check_blocked")
    assert len(entries) == 1

    created = await audit_repo.list_filtered(action="do_not_contact_entry_created")
    assert len(created) == 1


# -- review approval ------------------------------------------------------------


async def test_audit_log_created_on_review_approval(audit_repo, crm_fakes):
    companies = crm_fakes[get_company_repository]
    email_drafts = crm_fakes[get_email_draft_repository]
    company = await companies.create(Company(name="ReviewAuditCo", domain="review-audit.example"))
    draft = await email_drafts.create(
        EmailDraft(
            company_id=company.id,
            email_body="Hallo",
            review_status=EmailDraftReviewStatus.NEEDS_REVIEW,
        )
    )

    response = client.post(
        f"/api/v1/reviews/email-drafts/{draft.id}/status",
        json={"review_status": "approved"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200

    entries = await audit_repo.list_filtered(action="review_approved")
    assert len(entries) == 1


# -- external draft creation ----------------------------------------------------


async def test_audit_log_created_on_external_draft_creation(audit_repo, crm_fakes):
    companies = crm_fakes[get_company_repository]
    email_drafts = crm_fakes[get_email_draft_repository]
    company = await companies.create(
        Company(name="ExternalDraftAuditCo", domain="ext-draft-audit.example")
    )
    draft = await email_drafts.create(
        EmailDraft(
            company_id=company.id,
            email_body="Hallo",
            review_status=EmailDraftReviewStatus.APPROVED,
        )
    )

    response = client.post(
        f"/api/v1/email-drafts/{draft.id}/external-draft",
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200

    started = await audit_repo.list_filtered(action="external_draft_creation_started")
    succeeded = await audit_repo.list_filtered(
        action="external_draft_creation_succeeded"
    )
    assert len(started) == 1
    assert len(succeeded) == 1


# -- reply sync -------------------------------------------------------------------


async def test_audit_log_created_on_reply_sync(audit_repo, crm_fakes):
    response = client.post(
        "/api/v1/replies/sync-recent", headers=_auth_header("admin")
    )
    assert response.status_code == 200

    started = await audit_repo.list_filtered(action="reply_sync_started")
    completed = await audit_repo.list_filtered(action="reply_sync_completed")
    assert len(started) == 1
    assert len(completed) == 1


# -- no secrets ---------------------------------------------------------------


async def test_audit_logs_never_contain_a_secret_like_value(audit_repo, crm_fakes):
    client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "SecretCheckCo", "product_or_service_offered": "X"},
        headers=_auth_header("admin"),
    )
    entries = await audit_repo.list_filtered(limit=500)
    serialized = str([vars(e) for e in entries])
    for secret_like in _SECRET_LIKE_VALUES:
        assert secret_like not in serialized


# -- role gating ----------------------------------------------------------------


def test_audit_logs_endpoint_without_token_returns_401():
    response = client.get("/api/v1/audit-logs")
    assert response.status_code == 401


def test_audit_logs_endpoint_allowed_for_admin(audit_repo):
    response = client.get("/api/v1/audit-logs", headers=_auth_header("admin"))
    assert response.status_code == 200


def test_audit_logs_endpoint_blocked_for_sales(audit_repo):
    response = client.get("/api/v1/audit-logs", headers=_auth_header("sales"))
    assert response.status_code == 403


def test_audit_logs_endpoint_blocked_for_reviewer(audit_repo):
    response = client.get("/api/v1/audit-logs", headers=_auth_header("reviewer"))
    assert response.status_code == 403


def test_audit_log_detail_blocked_for_non_admin(audit_repo):
    response = client.get(
        f"/api/v1/audit-logs/{uuid.uuid4()}", headers=_auth_header("sales")
    )
    assert response.status_code == 403


def test_audit_log_detail_returns_404_for_unknown_id(audit_repo):
    response = client.get(
        f"/api/v1/audit-logs/{uuid.uuid4()}", headers=_auth_header("admin")
    )
    assert response.status_code == 404
