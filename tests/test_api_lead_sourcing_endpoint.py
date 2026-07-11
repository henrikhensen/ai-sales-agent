"""Integration tests for the Lead Sourcing API.

Covers auth/role gating (GET/status/candidates: admin/sales/reviewer;
POST campaigns/PATCH/runs/import: admin/sales; archive: admin only;
approve/reject: admin/sales/reviewer), end-to-end campaign->run->approve
flow through the real HTTP stack, and the standing no-send-capability
regression checks.
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
    get_user_repository,
    get_website_research_service,
)
from backend.main import app
from tests.conftest import (
    FakeCompanyRepository,
    FakeDoNotContactRepository,
    FakeICPProfileRepository,
    FakeLeadCandidateRepository,
    FakeLeadRepository,
    FakeLeadSourcingCampaignRepository,
    FakeLeadSourcingRunRepository,
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
        get_website_research_service: FakeWebsiteResearchService(),
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
    payload = {"name": "Test Campaign", "target_industry": "Logistics", **overrides}
    response = client.post(
        "/api/v1/lead-sourcing/campaigns", json=payload, headers=_auth_header(role)
    )
    assert response.status_code == 201, response.text
    return response.json()


# -- status ------------------------------------------------------------------------


def test_status_without_token_returns_401():
    response = client.get("/api/v1/lead-sourcing/status")
    assert response.status_code == 401


@pytest.mark.parametrize("role", ["admin", "sales", "reviewer"])
def test_status_allowed_for_every_role(role):
    response = client.get("/api/v1/lead-sourcing/status", headers=_auth_header(role))
    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["real_search_enabled"] is False


def test_status_reflects_brave_provider_without_ever_exposing_the_key():
    from backend.shared.config import get_settings

    settings = get_settings()
    original = {
        "lead_sourcing_provider": settings.lead_sourcing_provider,
        "lead_sourcing_enable_real_search": settings.lead_sourcing_enable_real_search,
        "brave_search_api_key": settings.brave_search_api_key,
    }
    settings.lead_sourcing_provider = "brave"
    settings.lead_sourcing_enable_real_search = True
    settings.brave_search_api_key = "sk-real-secret-brave-key-value"
    try:
        response = client.get(
            "/api/v1/lead-sourcing/status", headers=_auth_header("sales")
        )
        assert response.status_code == 200
        body = response.json()
        assert body["provider"] == "brave"
        assert body["real_search_enabled"] is True
        assert body["status"] == "ready"
        assert "sk-real-secret-brave-key-value" not in response.text
        assert "brave_search_api_key" not in body
        assert "api_key" not in response.text.lower()
    finally:
        for key, value in original.items():
            setattr(settings, key, value)


# -- campaigns: auth/role gating ---------------------------------------------------


def test_list_campaigns_without_token_returns_401():
    response = client.get("/api/v1/lead-sourcing/campaigns")
    assert response.status_code == 401


def test_create_campaign_forbidden_for_reviewer():
    response = client.post(
        "/api/v1/lead-sourcing/campaigns",
        json={"name": "x"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_archive_campaign_forbidden_for_sales():
    created = _create_campaign()
    response = client.patch(
        f"/api/v1/lead-sourcing/campaigns/{created['id']}/archive",
        headers=_auth_header("sales"),
    )
    assert response.status_code == 403


# -- campaigns: CRUD ------------------------------------------------------------


def test_campaign_kann_erstellt_werden():
    created = _create_campaign()
    assert created["status"] == "draft"
    assert created["source_type"] == "mock"


def test_campaign_kann_aktualisiert_werden():
    created = _create_campaign()
    response = client.patch(
        f"/api/v1/lead-sourcing/campaigns/{created['id']}",
        json={"name": "Renamed"},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_campaign_kann_archiviert_werden():
    created = _create_campaign()
    response = client.patch(
        f"/api/v1/lead-sourcing/campaigns/{created['id']}/archive",
        headers=_auth_header("admin"),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "archived"


def test_get_missing_campaign_returns_404():
    response = client.get(
        f"/api/v1/lead-sourcing/campaigns/{uuid.uuid4()}", headers=_auth_header("admin")
    )
    assert response.status_code == 404


# -- runs -----------------------------------------------------------------------


def test_run_kann_gestartet_werden_und_kandidaten_koennen_approved_werden():
    created = _create_campaign()
    response = client.post(
        f"/api/v1/lead-sourcing/campaigns/{created['id']}/runs",
        json={"campaign_id": created["id"], "dry_run": False},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["run"]["status"] == "completed"
    assert len(body["candidates"]) > 0

    candidate_id = body["candidates"][0]["id"]
    approve_response = client.post(
        f"/api/v1/lead-sourcing/candidates/{candidate_id}/approve",
        json={},
        headers=_auth_header("sales"),
    )
    assert approve_response.status_code == 200, approve_response.text
    approved_body = approve_response.json()
    assert approved_body["candidate"]["review_status"] == "approved"
    assert approved_body["crm_company_id"] is not None
    assert approved_body["crm_lead_id"] is not None


def test_dry_run_response_marks_candidates_as_not_persisted():
    created = _create_campaign()
    response = client.post(
        f"/api/v1/lead-sourcing/campaigns/{created['id']}/runs",
        json={"campaign_id": created["id"], "dry_run": True},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["dry_run"] is True
    assert all(c["id"] is None for c in body["candidates"])


def test_start_run_forbidden_for_reviewer():
    created = _create_campaign()
    response = client.post(
        f"/api/v1/lead-sourcing/campaigns/{created['id']}/runs",
        json={"campaign_id": created["id"]},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_reject_candidate_works():
    created = _create_campaign()
    run_response = client.post(
        f"/api/v1/lead-sourcing/campaigns/{created['id']}/runs",
        json={"campaign_id": created["id"]},
        headers=_auth_header("admin"),
    )
    candidate_id = run_response.json()["candidates"][0]["id"]
    response = client.post(
        f"/api/v1/lead-sourcing/candidates/{candidate_id}/reject",
        json={"reason": "not relevant"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 200
    assert response.json()["candidate"]["review_status"] == "rejected"


# -- manual import ----------------------------------------------------------------


def test_kandidaten_import_funktioniert():
    created = _create_campaign()
    response = client.post(
        "/api/v1/lead-sourcing/candidates/import",
        json={
            "campaign_id": created["id"],
            "raw_text": "Acme Import GmbH, acme-import.example, https://acme-import.example, met at a conference",
        },
        headers=_auth_header("sales"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_imported"] == 1


def test_import_forbidden_for_reviewer():
    created = _create_campaign()
    response = client.post(
        "/api/v1/lead-sourcing/candidates/import",
        json={"campaign_id": created["id"], "raw_text": "Acme, acme.example,,"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


# -- regression: no send capability ------------------------------------------------


def test_kein_send_endpoint_unter_lead_sourcing():
    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/lead-sourcing"):
            assert "send" not in path.lower()
            assert "outreach" not in path.lower()
