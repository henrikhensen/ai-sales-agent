"""Tests for backend/shared/rate_limit.py and its application to
login/register, sales workflow, LLM test, and reply sync endpoints.

The global ``_test_safety_defaults`` fixture (tests/conftest.py) raises
every rate limit ceiling to 1,000,000 so the rest of the test suite never
trips them. Each test here locally lowers one specific limit back down via
``monkeypatch`` and resets the in-memory counter first, so tests never
bleed into each other.
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
    get_quality_score_repository,
    get_reply_repository,
    get_user_feedback_repository,
    get_user_repository,
    get_workflow_run_repository,
)
from backend.main import app
from backend.shared.config import get_settings
from backend.shared.rate_limit import check_rate_limit, reset_memory_store
from tests.conftest import (
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
    FakeUserFeedbackRepository,
    FakeUserRepository,
    FakeWorkflowRunRepository,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fake_user_repository():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = lambda: fake_repo
    yield fake_repo
    app.dependency_overrides.pop(get_user_repository, None)


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


# -- unit-level ---------------------------------------------------------------


async def test_check_rate_limit_allows_up_to_the_limit_then_blocks():
    reset_memory_store()
    settings = get_settings()
    key = f"unit-test:{uuid.uuid4()}"

    first = await check_rate_limit(key, limit=2, window_seconds=60, settings=settings)
    second = await check_rate_limit(key, limit=2, window_seconds=60, settings=settings)
    third = await check_rate_limit(key, limit=2, window_seconds=60, settings=settings)

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False
    assert third.retry_after_seconds > 0


# -- login / register spam ---------------------------------------------------


def test_rate_limit_blocks_login_spam(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 2)
    reset_memory_store()

    email = f"spam-{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpassword123"},
    )

    responses = [
        client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrong-password"},
        )
        for _ in range(4)
    ]

    statuses = [r.status_code for r in responses]
    assert 429 in statuses
    blocked = next(r for r in responses if r.status_code == 429)
    assert "retry-after" in {k.lower() for k in blocked.headers.keys()}
    reset_memory_store()


def test_rate_limit_returns_clear_error_message(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 1)
    reset_memory_store()

    email = f"spam2-{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpassword123"},
    )
    client.post(
        "/api/v1/auth/register",
        json={"email": f"other-{uuid.uuid4().hex[:8]}@example.com", "password": "testpassword123"},
    )
    response = client.post(
        "/api/v1/auth/register",
        json={"email": f"third-{uuid.uuid4().hex[:8]}@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 429
    assert "rate limit" in response.json()["detail"].lower()
    reset_memory_store()


# -- sales workflow spam ------------------------------------------------------


def test_rate_limit_blocks_sales_workflow_spam(monkeypatch):
    fake_repos = {
        get_company_repository: FakeCompanyRepository(),
        get_contact_repository: FakeContactRepository(),
        get_lead_repository: FakeLeadRepository(),
        get_workflow_run_repository: FakeWorkflowRunRepository(),
        get_email_draft_repository: FakeEmailDraftRepository(),
        get_do_not_contact_repository: FakeDoNotContactRepository(),
        get_interaction_repository: FakeInteractionRepository(),
        get_user_repository: FakeUserRepository(),
        get_quality_score_repository: FakeQualityScoreRepository(),
        get_user_feedback_repository: FakeUserFeedbackRepository(),
    }
    for dep, fake in fake_repos.items():
        app.dependency_overrides[dep] = _returning(fake)

    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_workflow_per_hour", 1)
    reset_memory_store()

    try:
        headers = _auth_header("admin")
        payload = {
            "company_name": "RateLimitTestCo",
            "product_or_service_offered": "Testing",
        }
        first = client.post("/api/v1/workflows/sales", json=payload, headers=headers)
        second = client.post("/api/v1/workflows/sales", json=payload, headers=headers)

        assert first.status_code == 200
        assert second.status_code == 429
    finally:
        for dep in fake_repos:
            app.dependency_overrides.pop(dep, None)
        reset_memory_store()


# -- llm test spam ------------------------------------------------------------


def test_rate_limit_blocks_llm_test_spam(monkeypatch):
    app.dependency_overrides[get_user_repository] = _returning(FakeUserRepository())
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_llm_test_per_hour", 1)
    reset_memory_store()

    try:
        headers = _auth_header("admin")
        first = client.post("/api/v1/settings/llm/test", headers=headers)
        second = client.post("/api/v1/settings/llm/test", headers=headers)

        assert first.status_code == 200
        assert second.status_code == 429
    finally:
        app.dependency_overrides.pop(get_user_repository, None)
        reset_memory_store()


# -- reply sync spam ----------------------------------------------------------


def test_rate_limit_blocks_reply_sync_spam(monkeypatch):
    fake_repos = {
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
        get_user_repository: FakeUserRepository(),
    }
    for dep, fake in fake_repos.items():
        app.dependency_overrides[dep] = _returning(fake)

    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_reply_sync_per_hour", 1)
    reset_memory_store()

    try:
        headers = _auth_header("admin")
        first = client.post("/api/v1/replies/sync-recent", headers=headers)
        second = client.post("/api/v1/replies/sync-recent", headers=headers)

        assert first.status_code == 200
        assert second.status_code == 429
    finally:
        for dep in fake_repos:
            app.dependency_overrides.pop(dep, None)
        reset_memory_store()


def test_rate_limit_disabled_setting_bypasses_all_checks(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 1)
    reset_memory_store()

    email = f"nolimit-{uuid.uuid4().hex[:8]}@example.com"
    responses = [
        client.post(
            "/api/v1/auth/register",
            json={"email": f"{i}-{email}", "password": "testpassword123"},
        )
        for i in range(3)
    ]
    assert all(r.status_code == 201 for r in responses)
    reset_memory_store()
