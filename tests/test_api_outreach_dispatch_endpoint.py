"""Integration tests for the Controlled Outreach Dispatch API.

Covers auth/role gating, an end-to-end readiness -> create -> compliance-ack
-> confirm flow through the real HTTP stack (mock provider, never a
network call), the dispatch rate limit, and the standing regression checks
that no batch-send/reply-send/general-send endpoint exists anywhere.
"""

import uuid

import anyio
import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_company_repository,
    get_contact_repository,
    get_do_not_contact_repository,
    get_email_draft_repository,
    get_email_provider_connection_repository,
    get_external_email_draft_repository,
    get_icp_profile_repository,
    get_interaction_repository,
    get_lead_candidate_repository,
    get_lead_repository,
    get_offer_profile_repository,
    get_outreach_campaign_repository,
    get_outreach_dispatch_repository,
    get_outreach_queue_item_repository,
    get_qualification_result_repository,
    get_user_repository,
    get_workflow_run_repository,
)
from backend.main import app
from backend.shared.config import get_settings
from backend.shared.rate_limit import reset_memory_store
from tests.conftest import (
    FakeCompanyRepository,
    FakeContactRepository,
    FakeDoNotContactRepository,
    FakeEmailDraftRepository,
    FakeEmailProviderConnectionRepository,
    FakeExternalEmailDraftRepository,
    FakeICPProfileRepository,
    FakeInteractionRepository,
    FakeLeadCandidateRepository,
    FakeLeadRepository,
    FakeOfferProfileRepository,
    FakeOutreachCampaignRepository,
    FakeOutreachDispatchRepository,
    FakeOutreachQueueItemRepository,
    FakeQualificationResultRepository,
    FakeUserRepository,
    FakeWorkflowRunRepository,
)

client = TestClient(app)

_FULL_ACK = {
    "contact_permission_confirmed": True,
    "do_not_contact_confirmed": True,
    "human_review_confirmed": True,
    "draft_or_controlled_send_confirmed": True,
    "legal_responsibility_confirmed": True,
}


def _returning(fake):
    def _get():
        return fake

    return _get


@pytest.fixture(autouse=True)
def _fake_repositories():
    overrides = {
        get_user_repository: FakeUserRepository(),
        get_company_repository: FakeCompanyRepository(),
        get_lead_repository: FakeLeadRepository(),
        get_contact_repository: FakeContactRepository(),
        get_interaction_repository: FakeInteractionRepository(),
        get_email_draft_repository: FakeEmailDraftRepository(),
        get_do_not_contact_repository: FakeDoNotContactRepository(),
        get_workflow_run_repository: FakeWorkflowRunRepository(),
        get_icp_profile_repository: FakeICPProfileRepository(),
        get_offer_profile_repository: FakeOfferProfileRepository(),
        get_lead_candidate_repository: FakeLeadCandidateRepository(),
        get_qualification_result_repository: FakeQualificationResultRepository(),
        get_outreach_campaign_repository: FakeOutreachCampaignRepository(),
        get_outreach_queue_item_repository: FakeOutreachQueueItemRepository(),
        get_outreach_dispatch_repository: FakeOutreachDispatchRepository(),
        get_email_provider_connection_repository: FakeEmailProviderConnectionRepository(),
        get_external_email_draft_repository: FakeExternalEmailDraftRepository(),
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


async def _seed_ready_queue_item(fakes, *, domain: str = "acme.example.com") -> str:
    from backend.domain.entities.company import Company
    from backend.domain.entities.email_draft import EmailDraft
    from backend.domain.entities.lead_candidate import LeadCandidate
    from backend.domain.entities.outreach_queue_item import OutreachQueueItem
    from backend.domain.enums import EmailDraftReviewStatus

    companies = fakes[get_company_repository]
    email_drafts = fakes[get_email_draft_repository]
    lead_candidates = fakes[get_lead_candidate_repository]
    queue_items = fakes[get_outreach_queue_item_repository]

    company = await companies.create(Company(name="Acme GmbH", domain=domain, industry="Logistics"))
    candidate = await lead_candidates.create(
        LeadCandidate(
            sourcing_run_id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            company_name=company.name,
            company_domain=domain,
            public_contact_email=f"info@{domain}",
        )
    )
    draft = await email_drafts.create(
        EmailDraft(
            company_id=company.id,
            email_body="Full email body text used only for the internal draft.",
            subject_lines=["Quick question"],
            review_status=EmailDraftReviewStatus.APPROVED,
        )
    )
    item = await queue_items.create(
        OutreachQueueItem(
            campaign_id=uuid.uuid4(),
            company_id=company.id,
            lead_candidate_id=candidate.id,
            email_draft_id=draft.id,
            queue_status="approved",
            qualification_score=90,
            qualification_level="excellent",
        )
    )
    return str(item.id)


# -- auth / role gating ---------------------------------------------------------


def test_dashboard_ohne_token_gibt_401():
    response = client.get("/api/v1/outreach/dispatch/dashboard")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_dashboard_erlaubt_fuer_jede_rolle(role):
    response = client.get("/api/v1/outreach/dispatch/dashboard", headers=_auth_header(role))
    assert response.status_code == 200
    body = response.json()
    assert body["dispatch_mode"] == "draft_only"
    assert body["real_send_enabled"] is False


def test_readiness_check_verboten_fuer_reviewer(_fake_repositories):
    item_id = anyio.run(_seed_ready_queue_item, _fake_repositories)
    response = client.post(
        f"/api/v1/outreach/queue/{item_id}/dispatch/readiness",
        json={},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_confirm_verboten_fuer_reviewer(_fake_repositories):
    item_id = anyio.run(_seed_ready_queue_item, _fake_repositories)
    create_response = client.post(
        f"/api/v1/outreach/queue/{item_id}/dispatch",
        json={},
        headers=_auth_header("sales"),
    )
    dispatch_id = create_response.json()["dispatch"]["id"]
    response = client.post(
        f"/api/v1/outreach/dispatch/{dispatch_id}/confirm",
        json={},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


# -- end-to-end flow -----------------------------------------------------------


def test_readiness_dispatch_ack_confirm_end_to_end(_fake_repositories):
    item_id = anyio.run(_seed_ready_queue_item, _fake_repositories)
    header = _auth_header("sales")

    readiness_response = client.post(
        f"/api/v1/outreach/queue/{item_id}/dispatch/readiness", json={}, headers=header
    )
    assert readiness_response.status_code == 200, readiness_response.text
    assert readiness_response.json()["is_ready"] is True

    create_response = client.post(
        f"/api/v1/outreach/queue/{item_id}/dispatch", json={}, headers=header
    )
    assert create_response.status_code == 200, create_response.text
    dispatch = create_response.json()["dispatch"]
    assert dispatch["dispatch_status"] == "pending"

    ack_response = client.post(
        f"/api/v1/outreach/dispatch/{dispatch['id']}/compliance-ack",
        json=_FULL_ACK,
        headers=header,
    )
    assert ack_response.status_code == 200, ack_response.text
    assert ack_response.json()["dispatch"]["dispatch_status"] == "ready"

    confirm_response = client.post(
        f"/api/v1/outreach/dispatch/{dispatch['id']}/confirm", json={}, headers=header
    )
    assert confirm_response.status_code == 200, confirm_response.text
    confirmed = confirm_response.json()["dispatch"]
    assert confirmed["dispatch_status"] == "external_draft_created"

    queue_response = client.get(
        f"/api/v1/outreach/queue/{item_id}", headers=header
    )
    assert queue_response.json()["queue_status"] == "external_draft_created"


def test_confirm_ohne_ack_gibt_409(_fake_repositories):
    item_id = anyio.run(_seed_ready_queue_item, _fake_repositories)
    header = _auth_header("sales")
    create_response = client.post(
        f"/api/v1/outreach/queue/{item_id}/dispatch", json={}, headers=header
    )
    dispatch_id = create_response.json()["dispatch"]["id"]

    response = client.post(
        f"/api/v1/outreach/dispatch/{dispatch_id}/confirm", json={}, headers=header
    )
    assert response.status_code == 409


def test_cancel_dispatch(_fake_repositories):
    item_id = anyio.run(_seed_ready_queue_item, _fake_repositories)
    header = _auth_header("sales")
    create_response = client.post(
        f"/api/v1/outreach/queue/{item_id}/dispatch", json={}, headers=header
    )
    dispatch_id = create_response.json()["dispatch"]["id"]

    response = client.post(
        f"/api/v1/outreach/dispatch/{dispatch_id}/cancel",
        json={"reason": "test"},
        headers=header,
    )
    assert response.status_code == 200
    assert response.json()["dispatch"]["dispatch_status"] == "cancelled"


def test_get_missing_dispatch_gibt_404():
    response = client.get(
        f"/api/v1/outreach/dispatch/{uuid.uuid4()}", headers=_auth_header("admin")
    )
    assert response.status_code == 404


def test_readiness_missing_queue_item_gibt_404():
    response = client.post(
        f"/api/v1/outreach/queue/{uuid.uuid4()}/dispatch/readiness",
        json={},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 404


# -- rate limit ------------------------------------------------------------------


def test_rate_limit_outreach_dispatch(monkeypatch, _fake_repositories):
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_outreach_dispatch_per_hour", 2)
    reset_memory_store()
    try:
        header = _auth_header("admin")
        codes = []
        for _ in range(3):
            item_id = anyio.run(_seed_ready_queue_item, _fake_repositories)
            response = client.post(
                f"/api/v1/outreach/queue/{item_id}/dispatch/readiness",
                json={},
                headers=header,
            )
            codes.append(response.status_code)
        assert 429 in codes
    finally:
        reset_memory_store()


# -- regression: no send capability ------------------------------------------------


def test_kein_allgemeiner_send_endpoint_unter_outreach():
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/outreach"):
            assert "send" not in path.lower()


def test_kein_reply_send_endpoint():
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/replies"):
            assert "send" not in path.lower()


def test_kein_batch_endpoint_unter_dispatch():
    for route in app.routes:
        path = getattr(route, "path", "")
        if "/dispatch" in path:
            assert "batch" not in path.lower()


def test_dispatch_dashboard_zeigt_keine_secrets():
    response = client.get(
        "/api/v1/outreach/dispatch/dashboard", headers=_auth_header("admin")
    )
    body_text = response.text.lower()
    for forbidden in ("token", "secret", "api_key", "client_id", "client_secret"):
        assert forbidden not in body_text
