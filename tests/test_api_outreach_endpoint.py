"""Integration tests for the Outreach Campaign Queue API.

Covers auth/role gating, an end-to-end campaign -> build-queue ->
prepare-workflow flow through the real HTTP stack (Sales Workflow runs
against the deterministic MockLLMProvider — never a network call), the
outreach rate limits, and the standing no-send-capability regression
checks (no send endpoint, no 'sent'/external-draft-auto-create route).
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_company_repository,
    get_contact_repository,
    get_do_not_contact_repository,
    get_email_draft_repository,
    get_icp_profile_repository,
    get_interaction_repository,
    get_lead_candidate_repository,
    get_lead_repository,
    get_offer_profile_repository,
    get_outreach_campaign_repository,
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
    FakeICPProfileRepository,
    FakeInteractionRepository,
    FakeLeadCandidateRepository,
    FakeLeadRepository,
    FakeOfferProfileRepository,
    FakeOutreachCampaignRepository,
    FakeOutreachQueueItemRepository,
    FakeQualificationResultRepository,
    FakeUserRepository,
    FakeWorkflowRunRepository,
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


def _create_campaign(role: str = "admin", **overrides) -> dict:
    payload = {"name": "Q3 Logistics Push", **overrides}
    response = client.post(
        "/api/v1/outreach/campaigns", json=payload, headers=_auth_header(role)
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _seed_qualification_result(fakes, *, domain: str = "acme.example.com") -> dict:
    from backend.domain.entities.company import Company
    from backend.domain.entities.lead import Lead
    from backend.domain.entities.qualification_result import QualificationResult
    from backend.domain.enums import LeadSource

    companies = fakes[get_company_repository]
    leads = fakes[get_lead_repository]
    results = fakes[get_qualification_result_repository]

    company = await companies.create(Company(name="Acme GmbH", domain=domain, industry="Logistics"))
    lead = await leads.create(Lead(company_id=company.id, source=LeadSource.OUTBOUND))
    result = await results.create(
        QualificationResult(
            qualification_run_id=uuid.uuid4(),
            lead_id=lead.id,
            company_id=company.id,
            qualification_score=90,
            qualification_level="excellent",
            qualification_status="priority",
            recommended_outreach_angle="Fleet visibility angle.",
            duplicate_status="new",
            compliance_status="clear",
            do_not_contact_status="clear",
        )
    )
    return {"result_id": str(result.id), "lead_id": str(lead.id), "company_id": str(company.id)}


# -- auth / role gating ---------------------------------------------------------


def test_campaigns_ohne_token_gibt_401():
    response = client.get("/api/v1/outreach/campaigns")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_status_erlaubt_fuer_jede_rolle(role):
    response = client.get("/api/v1/outreach/status", headers=_auth_header(role))
    assert response.status_code == 200
    assert response.json()["auto_create_external_drafts"] is False


def test_create_campaign_verboten_fuer_reviewer():
    response = client.post(
        "/api/v1/outreach/campaigns",
        json={"name": "Reviewer campaign"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_create_campaign_erlaubt_fuer_sales():
    response = client.post(
        "/api/v1/outreach/campaigns",
        json={"name": "Sales campaign"},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "draft"


def test_prepare_batch_verboten_fuer_reviewer():
    campaign = _create_campaign()
    response = client.post(
        f"/api/v1/outreach/campaigns/{campaign['id']}/prepare-batch",
        json={},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


# -- end-to-end flow -----------------------------------------------------------


def test_queue_build_und_prepare_workflow_end_to_end(_fake_repositories):
    import anyio

    seeded = anyio.run(_seed_qualification_result, _fake_repositories)

    campaign = _create_campaign()

    build_response = client.post(
        f"/api/v1/outreach/campaigns/{campaign['id']}/build-queue",
        json={"qualification_result_ids": [seeded["result_id"]]},
        headers=_auth_header("admin"),
    )
    assert build_response.status_code == 200, build_response.text
    build_body = build_response.json()
    assert len(build_body["items"]) == 1
    item_id = build_body["items"][0]["id"]
    assert build_body["items"][0]["queue_status"] == "queued"

    prepare_response = client.post(
        f"/api/v1/outreach/queue/{item_id}/prepare-workflow",
        json={},
        headers=_auth_header("sales"),
    )
    assert prepare_response.status_code == 200, prepare_response.text
    prepare_body = prepare_response.json()
    assert prepare_body["blocked"] is False
    assert prepare_body["workflow_id"] is not None
    assert prepare_body["item"]["queue_status"] in ("workflow_prepared", "review_pending")


def test_dry_run_queue_build_persistiert_nichts(_fake_repositories):
    import anyio

    seeded = anyio.run(_seed_qualification_result, _fake_repositories)
    campaign = _create_campaign()

    response = client.post(
        f"/api/v1/outreach/campaigns/{campaign['id']}/build-queue",
        json={"qualification_result_ids": [seeded["result_id"]], "dry_run": True},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert body["items"][0]["id"] is None

    listed = client.get(
        f"/api/v1/outreach/queue?campaign_id={campaign['id']}", headers=_auth_header("admin")
    )
    assert listed.json()["items"] == []


def test_get_missing_campaign_gibt_404():
    response = client.get(
        f"/api/v1/outreach/campaigns/{uuid.uuid4()}", headers=_auth_header("admin")
    )
    assert response.status_code == 404


def test_get_missing_queue_item_gibt_404():
    response = client.get(
        f"/api/v1/outreach/queue/{uuid.uuid4()}", headers=_auth_header("admin")
    )
    assert response.status_code == 404


def test_ungueltiger_status_uebergang_gibt_400(_fake_repositories):
    import anyio

    seeded = anyio.run(_seed_qualification_result, _fake_repositories)
    campaign = _create_campaign()
    build_response = client.post(
        f"/api/v1/outreach/campaigns/{campaign['id']}/build-queue",
        json={"qualification_result_ids": [seeded["result_id"]]},
        headers=_auth_header("admin"),
    )
    item_id = build_response.json()["items"][0]["id"]

    response = client.patch(
        f"/api/v1/outreach/queue/{item_id}/status",
        json={"queue_status": "approved"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 400


# -- rate limit ------------------------------------------------------------------


def test_rate_limit_outreach_queue_build(monkeypatch, _fake_repositories):
    import anyio

    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_outreach_queue_per_hour", 2)
    reset_memory_store()
    try:
        campaign = _create_campaign()
        header = _auth_header("admin")
        codes = []
        for _ in range(3):
            seeded = anyio.run(_seed_qualification_result, _fake_repositories)
            response = client.post(
                f"/api/v1/outreach/campaigns/{campaign['id']}/build-queue",
                json={"qualification_result_ids": [seeded["result_id"]], "dry_run": True},
                headers=header,
            )
            codes.append(response.status_code)
        assert 429 in codes
    finally:
        reset_memory_store()


# -- regression: no send capability ------------------------------------------------


def test_kein_send_endpoint_unter_outreach():
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/outreach"):
            assert "send" not in path.lower()


def test_kein_sent_status_in_schema():
    from backend.application.outreach.schemas import OutreachQueueStatus

    assert "sent" not in OutreachQueueStatus.__args__
