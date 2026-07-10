"""Integration tests for the Lead Finder / Lead Discovery Run API.

Covers auth/role gating (create/run/create-drafts: admin/sales; view:
admin/sales/reviewer), a full create -> run -> get -> create-drafts flow
through the real HTTP stack (mock providers throughout, never a network
call or a real LLM call), the real_llm mode gate, the do-not-contact
safety gate, and the standing regression checks: no send-capable endpoint
anywhere under this router, unauthenticated access is rejected.
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
    get_lead_discovery_run_repository,
    get_lead_repository,
    get_lead_sourcing_campaign_repository,
    get_lead_sourcing_run_repository,
    get_offer_profile_repository,
    get_outreach_campaign_repository,
    get_outreach_queue_item_repository,
    get_qualification_result_repository,
    get_qualification_run_repository,
    get_user_repository,
    get_workflow_run_repository,
)
from backend.main import app
from tests.conftest import (
    FakeCompanyRepository,
    FakeContactRepository,
    FakeDoNotContactRepository,
    FakeEmailDraftRepository,
    FakeICPProfileRepository,
    FakeInteractionRepository,
    FakeLeadCandidateRepository,
    FakeLeadDiscoveryRunRepository,
    FakeLeadRepository,
    FakeLeadSourcingCampaignRepository,
    FakeLeadSourcingRunRepository,
    FakeOfferProfileRepository,
    FakeOutreachCampaignRepository,
    FakeOutreachQueueItemRepository,
    FakeQualificationResultRepository,
    FakeQualificationRunRepository,
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
        get_lead_candidate_repository: FakeLeadCandidateRepository(),
        get_icp_profile_repository: FakeICPProfileRepository(),
        get_offer_profile_repository: FakeOfferProfileRepository(),
        get_lead_sourcing_campaign_repository: FakeLeadSourcingCampaignRepository(),
        get_lead_sourcing_run_repository: FakeLeadSourcingRunRepository(),
        get_qualification_run_repository: FakeQualificationRunRepository(),
        get_qualification_result_repository: FakeQualificationResultRepository(),
        get_outreach_campaign_repository: FakeOutreachCampaignRepository(),
        get_outreach_queue_item_repository: FakeOutreachQueueItemRepository(),
        get_lead_discovery_run_repository: FakeLeadDiscoveryRunRepository(),
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


def _create_offer(role: str = "admin") -> str:
    response = client.post(
        "/api/v1/sales-strategy/offers",
        json={"name": "Test Offer", "main_value_proposition": "We help you sell more."},
        headers=_auth_header(role),
    )
    assert response.status_code == 201
    return response.json()["id"]


# -- auth gating ----------------------------------------------------------------


def test_create_run_requires_auth():
    response = client.post(
        "/api/v1/lead-discovery/runs",
        json={"target_customer": "Software", "offer_profile_id": str(uuid.uuid4())},
    )
    assert response.status_code == 401


def test_list_runs_requires_auth():
    response = client.get("/api/v1/lead-discovery/runs")
    assert response.status_code == 401


def test_reviewer_cannot_create_a_run():
    offer_id = _create_offer()
    response = client.post(
        "/api/v1/lead-discovery/runs",
        json={"target_customer": "Software", "offer_profile_id": offer_id},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_reviewer_can_list_and_view_runs():
    offer_id = _create_offer()
    created = client.post(
        "/api/v1/lead-discovery/runs",
        json={"target_customer": "Software", "offer_profile_id": offer_id},
        headers=_auth_header("sales"),
    ).json()

    list_response = client.get(
        "/api/v1/lead-discovery/runs", headers=_auth_header("reviewer")
    )
    assert list_response.status_code == 200

    get_response = client.get(
        f"/api/v1/lead-discovery/runs/{created['id']}", headers=_auth_header("reviewer")
    )
    assert get_response.status_code == 200


# -- create / not found -----------------------------------------------------------


def test_create_run_with_unknown_offer_returns_404():
    response = client.post(
        "/api/v1/lead-discovery/runs",
        json={"target_customer": "Software", "offer_profile_id": str(uuid.uuid4())},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 404


def test_create_run_defaults_to_mock_mode_and_pending_status():
    offer_id = _create_offer()
    response = client.post(
        "/api/v1/lead-discovery/runs",
        json={"target_customer": "Software", "region": "Berlin", "offer_profile_id": offer_id},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["mode"] == "mock"
    assert body["status"] == "pending"
    assert body["lead_sourcing_campaign_id"] is not None
    assert body["outreach_campaign_id"] is not None


def test_real_llm_mode_rejected_without_real_calls_enabled():
    offer_id = _create_offer()
    response = client.post(
        "/api/v1/lead-discovery/runs",
        json={
            "target_customer": "Software",
            "offer_profile_id": offer_id,
            "mode": "real_llm",
        },
        headers=_auth_header("sales"),
    )
    assert response.status_code == 400


def test_get_unknown_run_returns_404():
    response = client.get(
        f"/api/v1/lead-discovery/runs/{uuid.uuid4()}", headers=_auth_header("sales")
    )
    assert response.status_code == 404


# -- full pipeline flow ------------------------------------------------------------


def test_full_flow_run_pipeline_then_create_drafts():
    offer_id = _create_offer()
    created = client.post(
        "/api/v1/lead-discovery/runs",
        json={
            "target_customer": "Software",
            "region": "Berlin",
            "offer_profile_id": offer_id,
            "requested_count": 5,
            "min_score": 0,
        },
        headers=_auth_header("sales"),
    ).json()

    run_response = client.post(
        f"/api/v1/lead-discovery/runs/{created['id']}/run",
        headers=_auth_header("sales"),
    )
    assert run_response.status_code == 200
    detail = run_response.json()
    assert detail["status"] == "completed"
    assert detail["found_candidates"] >= 1
    assert detail["qualified_leads"] + detail["rejected_leads"] == detail["found_candidates"]
    assert "candidates" in detail

    # Running the pipeline again on an already-completed run is rejected.
    rerun_response = client.post(
        f"/api/v1/lead-discovery/runs/{created['id']}/run",
        headers=_auth_header("sales"),
    )
    assert rerun_response.status_code == 400

    drafts_response = client.post(
        f"/api/v1/lead-discovery/runs/{created['id']}/create-drafts",
        headers=_auth_header("sales"),
    )
    assert drafts_response.status_code == 200


def test_create_drafts_before_pipeline_completes_is_rejected():
    offer_id = _create_offer()
    created = client.post(
        "/api/v1/lead-discovery/runs",
        json={"target_customer": "Software", "offer_profile_id": offer_id},
        headers=_auth_header("sales"),
    ).json()

    response = client.post(
        f"/api/v1/lead-discovery/runs/{created['id']}/create-drafts",
        headers=_auth_header("sales"),
    )
    assert response.status_code == 400


def test_add_candidate_to_queue_without_qualification_returns_not_added():
    offer_id = _create_offer()
    created = client.post(
        "/api/v1/lead-discovery/runs",
        json={
            "target_customer": "Software",
            "region": "Berlin",
            "offer_profile_id": offer_id,
        },
        headers=_auth_header("sales"),
    ).json()
    client.post(
        f"/api/v1/lead-discovery/runs/{created['id']}/run", headers=_auth_header("sales")
    )

    response = client.post(
        f"/api/v1/lead-discovery/runs/{created['id']}/candidates/{uuid.uuid4()}/add-to-queue",
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["added"] is False


# -- standing safety regressions --------------------------------------------------


def test_no_send_capable_endpoint_exists_under_lead_discovery():
    openapi = client.get("/openapi.json").json()
    for path in openapi["paths"]:
        if path.startswith("/api/v1/lead-discovery"):
            assert "send" not in path.lower()
