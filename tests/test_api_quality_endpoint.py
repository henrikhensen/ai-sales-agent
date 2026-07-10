"""Integration tests for the Quality Scoring / Feedback API.

Covers auth/role gating (status: any active user; dashboard/scores/
feedback lists: admin/sales/reviewer; feedback creation: any active user;
feedback review/archive: admin/reviewer only), a create-score/create-
feedback/review/archive flow through the real HTTP stack, and the
standing regression check that unauthenticated access is rejected.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_company_repository,
    get_do_not_contact_repository,
    get_email_draft_repository,
    get_icp_profile_repository,
    get_lead_candidate_repository,
    get_offer_profile_repository,
    get_outreach_queue_item_repository,
    get_qualification_result_repository,
    get_quality_score_repository,
    get_reply_repository,
    get_user_feedback_repository,
    get_user_repository,
    get_workflow_run_repository,
)
from backend.domain.entities.company import Company
from backend.domain.entities.email_draft import EmailDraft
from backend.main import app
from tests.conftest import (
    FakeCompanyRepository,
    FakeDoNotContactRepository,
    FakeEmailDraftRepository,
    FakeICPProfileRepository,
    FakeLeadCandidateRepository,
    FakeOfferProfileRepository,
    FakeOutreachQueueItemRepository,
    FakeQualificationResultRepository,
    FakeQualityScoreRepository,
    FakeReplyRepository,
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
        get_email_draft_repository: FakeEmailDraftRepository(),
        get_workflow_run_repository: FakeWorkflowRunRepository(),
        get_lead_candidate_repository: FakeLeadCandidateRepository(),
        get_qualification_result_repository: FakeQualificationResultRepository(),
        get_outreach_queue_item_repository: FakeOutreachQueueItemRepository(),
        get_reply_repository: FakeReplyRepository(),
        get_offer_profile_repository: FakeOfferProfileRepository(),
        get_icp_profile_repository: FakeICPProfileRepository(),
        get_do_not_contact_repository: FakeDoNotContactRepository(),
        get_quality_score_repository: FakeQualityScoreRepository(),
        get_user_feedback_repository: FakeUserFeedbackRepository(),
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


# -- auth gating ----------------------------------------------------------------


def test_quality_status_requires_auth():
    response = client.get("/api/v1/quality/status")
    assert response.status_code == 401


def test_quality_dashboard_requires_auth():
    response = client.get("/api/v1/quality/dashboard")
    assert response.status_code == 401


def test_quality_status_reachable_for_any_active_role():
    response = client.get("/api/v1/quality/status", headers=_auth_header("sales"))
    assert response.status_code == 200
    body = response.json()
    assert "message" in body


def test_quality_dashboard_forbidden_for_no_role_is_not_applicable_but_ok_for_sales():
    response = client.get("/api/v1/quality/dashboard", headers=_auth_header("sales"))
    assert response.status_code == 200


# -- scoring ----------------------------------------------------------------------


async def test_create_and_get_quality_score(_fake_repositories):
    email_drafts = _fake_repositories[get_email_draft_repository]
    companies = _fake_repositories[get_company_repository]
    company = await companies.create(Company(name="Acme", domain="acme.example"))
    draft = await email_drafts.create(
        EmailDraft(
            company_id=company.id,
            email_body="Hallo, kurze Frage zu Ihrem Unternehmen. Interesse an einem Call?",
            subject_lines=["Frage"],
        )
    )

    create_response = client.post(
        "/api/v1/quality/score",
        json={"entity_type": "email_draft", "entity_id": str(draft.id)},
        headers=_auth_header("sales"),
    )
    assert create_response.status_code == 201
    score = create_response.json()
    assert score["entity_id"] == str(draft.id)

    get_response = client.get(
        f"/api/v1/quality/scores/{score['id']}", headers=_auth_header("admin")
    )
    assert get_response.status_code == 200

    entity_scores_response = client.get(
        f"/api/v1/quality/entity/email_draft/{draft.id}/scores",
        headers=_auth_header("reviewer"),
    )
    assert entity_scores_response.status_code == 200
    assert entity_scores_response.json()["items"]


def test_get_quality_score_not_found_returns_404():
    response = client.get(
        f"/api/v1/quality/scores/{uuid.uuid4()}", headers=_auth_header("admin")
    )
    assert response.status_code == 404


# -- feedback -----------------------------------------------------------------


def test_any_active_user_can_create_feedback():
    response = client.post(
        "/api/v1/quality/feedback",
        json={
            "entity_type": "email_draft",
            "entity_id": str(uuid.uuid4()),
            "rating": 4,
            "feedback_type": "quality_issue",
            "feedback_text": "Too generic.",
        },
        headers=_auth_header("sales"),
    )
    assert response.status_code == 201
    assert response.json()["review_status"] == "open"


def test_reviewer_can_list_and_review_feedback():
    entity_id = str(uuid.uuid4())
    created = client.post(
        "/api/v1/quality/feedback",
        json={
            "entity_type": "reply",
            "entity_id": entity_id,
            "rating": 2,
            "feedback_type": "bug",
        },
        headers=_auth_header("sales"),
    ).json()

    list_response = client.get("/api/v1/quality/feedback", headers=_auth_header("reviewer"))
    assert list_response.status_code == 200

    review_response = client.patch(
        f"/api/v1/quality/feedback/{created['id']}/review",
        json={"review_status": "accepted"},
        headers=_auth_header("reviewer"),
    )
    assert review_response.status_code == 200
    assert review_response.json()["review_status"] == "accepted"


def test_sales_cannot_review_feedback():
    created = client.post(
        "/api/v1/quality/feedback",
        json={
            "entity_type": "reply",
            "entity_id": str(uuid.uuid4()),
            "rating": 2,
            "feedback_type": "bug",
        },
        headers=_auth_header("sales"),
    ).json()

    response = client.patch(
        f"/api/v1/quality/feedback/{created['id']}/review",
        json={"review_status": "accepted"},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 403


def test_archive_feedback_requires_admin_or_reviewer():
    created = client.post(
        "/api/v1/quality/feedback",
        json={
            "entity_type": "reply",
            "entity_id": str(uuid.uuid4()),
            "rating": 2,
            "feedback_type": "bug",
        },
        headers=_auth_header("sales"),
    ).json()

    forbidden = client.patch(
        f"/api/v1/quality/feedback/{created['id']}/archive",
        headers=_auth_header("sales"),
    )
    assert forbidden.status_code == 403

    allowed = client.patch(
        f"/api/v1/quality/feedback/{created['id']}/archive",
        headers=_auth_header("admin"),
    )
    assert allowed.status_code == 200
    assert allowed.json()["review_status"] == "archived"


def test_no_send_capable_endpoint_exists_under_quality():
    openapi = client.get("/openapi.json").json()
    for path in openapi["paths"]:
        if path.startswith("/api/v1/quality") or path.startswith("/api/v1/beta-test"):
            assert "send" not in path.lower()


# -- Phase 36: priority, general/UI feedback, Real-World Test Run linkage -----------


def test_any_active_user_can_create_general_ui_feedback():
    response = client.post(
        "/api/v1/quality/feedback",
        json={
            "entity_type": "general",
            "rating": 3,
            "feedback_type": "bug",
            "feedback_text": "Die Navigation ist verwirrend.",
        },
        headers=_auth_header("sales"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["entity_type"] == "general"
    assert body["entity_id"] is None
    assert body["priority"] == "medium"


def test_general_feedback_without_entity_id_from_reviewer_too():
    response = client.post(
        "/api/v1/quality/feedback",
        json={"entity_type": "general", "rating": 4, "feedback_type": "positive"},
        headers=_auth_header("reviewer"),
    )
    assert response.status_code == 201


def test_non_general_feedback_without_entity_id_is_rejected():
    response = client.post(
        "/api/v1/quality/feedback",
        json={"entity_type": "email_draft", "rating": 3, "feedback_type": "bug"},
        headers=_auth_header("sales"),
    )
    assert response.status_code == 422


def test_feedback_priority_round_trips():
    response = client.post(
        "/api/v1/quality/feedback",
        json={
            "entity_type": "reply",
            "entity_id": str(uuid.uuid4()),
            "rating": 1,
            "feedback_type": "bug",
            "priority": "high",
        },
        headers=_auth_header("sales"),
    )
    assert response.status_code == 201
    assert response.json()["priority"] == "high"


def test_feedback_can_reference_a_real_world_test_run_id():
    run_id = str(uuid.uuid4())
    response = client.post(
        "/api/v1/quality/feedback",
        json={
            "entity_type": "real_world_test_run",
            "entity_id": run_id,
            "rating": 5,
            "feedback_type": "good_result",
            "real_world_test_run_id": run_id,
        },
        headers=_auth_header("admin"),
    )
    assert response.status_code == 201
    assert response.json()["real_world_test_run_id"] == run_id


def test_feedback_list_filters_by_priority():
    client.post(
        "/api/v1/quality/feedback",
        json={
            "entity_type": "reply",
            "entity_id": str(uuid.uuid4()),
            "rating": 1,
            "feedback_type": "bug",
            "priority": "high",
        },
        headers=_auth_header("sales"),
    )
    response = client.get(
        "/api/v1/quality/feedback?priority=high", headers=_auth_header("admin")
    )
    assert response.status_code == 200
    assert all(item["priority"] == "high" for item in response.json()["items"])


def test_general_feedback_audit_call_does_not_crash_with_no_entity_id():
    """The audit log call in FeedbackService.create_feedback passes
    entity_id=None straight through for general feedback — this must
    never raise (a 500 here would mean the audit call chokes on None)."""
    response = client.post(
        "/api/v1/quality/feedback",
        json={"entity_type": "general", "rating": 3, "feedback_type": "bug"},
        headers=_auth_header("admin"),
    )
    assert response.status_code == 201
