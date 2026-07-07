"""Integration tests for the Lead Qualification API.

Covers auth/role gating (GET/status/dashboard/results: admin/sales/
reviewer; POST runs/candidates|leads/.../qualify: admin/sales; PATCH
review: admin/sales/reviewer), an end-to-end sourcing->qualify->review
flow through the real HTTP stack, the qualification rate limit, and the
standing no-send-capability regression checks.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_company_repository,
    get_do_not_contact_repository,
    get_icp_profile_repository,
    get_lead_candidate_repository,
    get_lead_repository,
    get_lead_sourcing_campaign_repository,
    get_lead_sourcing_run_repository,
    get_offer_profile_repository,
    get_qualification_result_repository,
    get_qualification_run_repository,
    get_user_repository,
    get_website_research_service,
)
from backend.main import app
from backend.shared.config import get_settings
from backend.shared.rate_limit import reset_memory_store
from tests.conftest import (
    FakeCompanyRepository,
    FakeDoNotContactRepository,
    FakeICPProfileRepository,
    FakeLeadCandidateRepository,
    FakeLeadRepository,
    FakeLeadSourcingCampaignRepository,
    FakeLeadSourcingRunRepository,
    FakeOfferProfileRepository,
    FakeQualificationResultRepository,
    FakeQualificationRunRepository,
    FakeUserRepository,
    FakeWebsiteResearchService,
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
        get_lead_sourcing_campaign_repository: FakeLeadSourcingCampaignRepository(),
        get_lead_sourcing_run_repository: FakeLeadSourcingRunRepository(),
        get_lead_candidate_repository: FakeLeadCandidateRepository(),
        get_company_repository: FakeCompanyRepository(),
        get_lead_repository: FakeLeadRepository(),
        get_do_not_contact_repository: FakeDoNotContactRepository(),
        get_icp_profile_repository: FakeICPProfileRepository(),
        get_offer_profile_repository: FakeOfferProfileRepository(),
        get_website_research_service: FakeWebsiteResearchService(),
        get_qualification_run_repository: FakeQualificationRunRepository(),
        get_qualification_result_repository: FakeQualificationResultRepository(),
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


def _source_candidates(role: str = "admin") -> list[dict]:
    campaign = client.post(
        "/api/v1/lead-sourcing/campaigns",
        json={"name": "Qual Test Campaign", "target_industry": "Logistics"},
        headers=_auth_header(role),
    ).json()
    run = client.post(
        f"/api/v1/lead-sourcing/campaigns/{campaign['id']}/runs",
        json={"campaign_id": campaign["id"]},
        headers=_auth_header(role),
    ).json()
    return run["candidates"]


# -- status / dashboard ----------------------------------------------------------


def test_status_without_token_returns_401():
    response = client.get("/api/v1/lead-qualification/status")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_status_allowed_for_every_role(role):
    response = client.get("/api/v1/lead-qualification/status", headers=_auth_header(role))
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["use_llm"] is False


def test_dashboard_allowed_for_every_role():
    response = client.get(
        "/api/v1/lead-qualification/dashboard", headers=_auth_header("reviewer")
    )
    assert response.status_code == 200


# -- role gating ---------------------------------------------------------------


def test_start_run_forbidden_for_reviewer():
    response = client.post(
        "/api/v1/lead-qualification/runs",
        json={"source_type": "lead_candidate", "lead_candidate_ids": []},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_qualify_candidate_forbidden_for_reviewer():
    candidates = _source_candidates()
    response = client.post(
        f"/api/v1/lead-qualification/candidates/{candidates[0]['id']}/qualify",
        json={},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_review_allowed_for_reviewer():
    candidates = _source_candidates()
    qualify_response = client.post(
        f"/api/v1/lead-qualification/candidates/{candidates[0]['id']}/qualify",
        json={},
        headers=_auth_header("admin"),
    )
    result_id = qualify_response.json()["id"]
    response = client.patch(
        f"/api/v1/lead-qualification/results/{result_id}/review",
        json={"qualification_status": "qualified"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 200


# -- end-to-end flow -----------------------------------------------------------


def test_lead_candidate_kann_qualifiziert_werden_end_to_end():
    candidates = _source_candidates()
    response = client.post(
        f"/api/v1/lead-qualification/candidates/{candidates[0]['id']}/qualify",
        json={},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["lead_candidate_id"] == candidates[0]["id"]
    assert "qualification_score" in body


def test_run_kann_gestartet_werden_end_to_end():
    candidates = _source_candidates()
    response = client.post(
        "/api/v1/lead-qualification/runs",
        json={
            "source_type": "lead_candidate",
            "lead_candidate_ids": [c["id"] for c in candidates],
        },
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["run"]["status"] == "completed"
    assert body["run"]["total_items"] == len(candidates)


def test_dry_run_flag_is_echoed_in_response():
    candidates = _source_candidates()
    response = client.post(
        "/api/v1/lead-qualification/runs",
        json={
            "source_type": "lead_candidate",
            "lead_candidate_ids": [candidates[0]["id"]],
            "dry_run": True,
        },
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    assert response.json()["dry_run"] is True


def test_get_missing_result_returns_404():
    response = client.get(
        f"/api/v1/lead-qualification/results/{uuid.uuid4()}", headers=_auth_header("admin")
    )
    assert response.status_code == 404


def test_qualify_missing_candidate_returns_404():
    response = client.post(
        f"/api/v1/lead-qualification/candidates/{uuid.uuid4()}/qualify",
        json={},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 404


# -- rate limit ------------------------------------------------------------------


def test_rate_limit_lead_qualification(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_lead_qualification_per_hour", 2)
    reset_memory_store()
    try:
        candidates = _source_candidates()
        header = _auth_header("admin")
        codes = []
        for candidate in candidates[:1]:
            for _ in range(3):
                response = client.post(
                    f"/api/v1/lead-qualification/candidates/{candidate['id']}/qualify",
                    json={},
                    headers=header,
                )
                codes.append(response.status_code)
        assert 429 in codes
    finally:
        reset_memory_store()


# -- regression: no send capability ------------------------------------------------


def test_kein_send_endpoint_unter_lead_qualification():
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/lead-qualification"):
            assert "send" not in path.lower()
            assert "outreach" not in path.lower()
