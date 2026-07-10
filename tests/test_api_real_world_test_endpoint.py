"""Integration tests for the Real-World Test Mode API (Phase 34).

Covers auth/role gating (create: admin/sales; view: admin/sales/reviewer;
abort: admin only), a full create -> list -> get -> abort flow through the
real HTTP stack (mock LLM provider, never a network call), the do-not-
contact safety gate, the real_llm mode gate, and the standing regression
checks: no send-capable endpoint anywhere, unauthenticated access is
rejected.
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
    get_quality_score_repository,
    get_real_world_test_run_repository,
    get_user_feedback_repository,
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
    FakeLeadRepository,
    FakeOfferProfileRepository,
    FakeQualityScoreRepository,
    FakeRealWorldTestRunRepository,
    FakeUserFeedbackRepository,
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
        get_quality_score_repository: FakeQualityScoreRepository(),
        get_user_feedback_repository: FakeUserFeedbackRepository(),
        get_real_world_test_run_repository: FakeRealWorldTestRunRepository(),
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


def test_create_run_requires_auth():
    response = client.post(
        "/api/v1/real-world-test-runs",
        json={"name": "Run", "company_name": "Acme"},
    )
    assert response.status_code == 401


def test_reviewer_cannot_create_run():
    response = client.post(
        "/api/v1/real-world-test-runs",
        json={"name": "Run", "company_name": "Acme"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 403


def test_reviewer_can_view_runs():
    client.post(
        "/api/v1/real-world-test-runs",
        json={"name": "Run", "company_name": "Acme"},
        headers=_auth_header("admin"),
    )
    response = client.get("/api/v1/real-world-test-runs", headers=_auth_header("reviewer"))
    assert response.status_code == 200


def test_sales_can_create_a_run_end_to_end():
    created = client.post(
        "/api/v1/real-world-test-runs",
        json={
            "name": "Sales Run",
            "company_name": "Acme GmbH",
            "product_or_service_offered": "Freight API",
        },
        headers=_auth_header("sales"),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "completed"
    assert body["mode"] == "safe"
    assert body["workflow_run_id"] is not None

    get_response = client.get(
        f"/api/v1/real-world-test-runs/{body['id']}", headers=_auth_header("sales")
    )
    assert get_response.status_code == 200
    assert get_response.json()["id"] == body["id"]


def test_get_run_not_found_returns_404():
    response = client.get(
        f"/api/v1/real-world-test-runs/{uuid.uuid4()}", headers=_auth_header("admin")
    )
    assert response.status_code == 404


def test_real_llm_mode_without_config_returns_400():
    response = client.post(
        "/api/v1/real-world-test-runs",
        json={"name": "Run", "company_name": "Acme", "mode": "real_llm"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 400


def test_do_not_contact_blocks_the_run():
    client.post(
        "/api/v1/compliance/do-not-contact",
        json={"domain": "blocked.example", "reason": "opt-out"},
        headers=_auth_header("admin"),
    )
    response = client.post(
        "/api/v1/real-world-test-runs",
        json={
            "name": "Blocked run",
            "company_name": "Blocked Co",
            "website_url": "https://blocked.example",
        },
        headers=_auth_header("admin"),
    )
    assert response.status_code == 201
    assert response.json()["status"] == "blocked"


def test_sales_cannot_abort_a_run():
    created = client.post(
        "/api/v1/real-world-test-runs",
        json={"name": "Run", "company_name": "Acme"},
        headers=_auth_header("admin"),
    ).json()
    response = client.post(
        f"/api/v1/real-world-test-runs/{created['id']}/abort",
        headers=_auth_header("sales"),
    )
    assert response.status_code == 403


def test_admin_can_abort_but_not_a_completed_run():
    created = client.post(
        "/api/v1/real-world-test-runs",
        json={"name": "Run", "company_name": "Acme"},
        headers=_auth_header("admin"),
    ).json()
    assert created["status"] == "completed"
    response = client.post(
        f"/api/v1/real-world-test-runs/{created['id']}/abort",
        headers=_auth_header("admin"),
    )
    assert response.status_code == 400


def test_no_send_capable_endpoint_exists_under_real_world_test():
    openapi = client.get("/openapi.json").json()
    for path in openapi["paths"]:
        if path.startswith("/api/v1/real-world-test-runs"):
            assert "send" not in path.lower()
