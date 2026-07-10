import uuid

import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_company_repository,
    get_contact_repository,
    get_do_not_contact_repository,
    get_email_draft_repository,
    get_interaction_repository,
    get_lead_repository,
    get_quality_score_repository,
    get_user_feedback_repository,
    get_user_repository,
    get_website_research_service,
    get_workflow_run_repository,
)
from backend.application.research.exceptions import InvalidWebsiteURLError
from backend.application.research.schemas import WebsiteResearchResponse
from backend.main import app
from tests.conftest import (
    FakeCompanyRepository,
    FakeContactRepository,
    FakeDoNotContactRepository,
    FakeEmailDraftRepository,
    FakeInteractionRepository,
    FakeLeadRepository,
    FakeQualityScoreRepository,
    FakeUserFeedbackRepository,
    FakeUserRepository,
    FakeWorkflowRunRepository,
)

# No context manager → lifespan (and thus DB init) does not run; the sales
# workflow only calls the existing agent services with the mock LLM provider
# and touches no external services. Every repository dependency is
# overridden below with an in-memory fake, so persistence (including CRM
# sync) is exercised without a real database.
client = TestClient(app)


@pytest.fixture(autouse=True)
def _fake_workflow_run_repository():
    fake_repo = FakeWorkflowRunRepository()
    app.dependency_overrides[get_workflow_run_repository] = lambda: fake_repo
    yield fake_repo
    app.dependency_overrides.pop(get_workflow_run_repository, None)


def _returning(fake):
    # A plain zero-argument closure. FastAPI inspects the signature of every
    # override callable as if it were a route dependency, so a lambda with
    # its own (default-valued) parameter — e.g. `lambda fake=fake: fake` —
    # gets misread as an injectable parameter instead of being called as-is.
    def _get():
        return fake

    return _get


@pytest.fixture(autouse=True)
def _fake_crm_repositories():
    fakes = {
        get_company_repository: FakeCompanyRepository(),
        get_lead_repository: FakeLeadRepository(),
        get_contact_repository: FakeContactRepository(),
        get_interaction_repository: FakeInteractionRepository(),
        get_email_draft_repository: FakeEmailDraftRepository(),
        get_do_not_contact_repository: FakeDoNotContactRepository(),
        get_quality_score_repository: FakeQualityScoreRepository(),
        get_user_feedback_repository: FakeUserFeedbackRepository(),
    }
    for dependency, fake in fakes.items():
        app.dependency_overrides[dependency] = _returning(fake)
    yield fakes
    for dependency in fakes:
        app.dependency_overrides.pop(dependency, None)


@pytest.fixture(autouse=True)
def _fake_user_repository():
    fake_repo = FakeUserRepository()
    app.dependency_overrides[get_user_repository] = _returning(fake_repo)
    yield fake_repo
    app.dependency_overrides.pop(get_user_repository, None)


def _login_as(role: str) -> str:
    """Register a fresh user with ``role`` and return a valid access token.

    Requires ``_fake_user_repository`` to already be active (it is,
    autouse). Since Role-Based Access Control now gates most CRM/Workflow
    endpoints, every test in this file runs as an admin by default (see
    ``_authenticated_as_admin`` below) unless it explicitly logs in as a
    different role.
    """
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


@pytest.fixture(autouse=True)
def _authenticated_as_admin(_fake_user_repository):
    # Admin can read/write everything this file's existing tests exercise,
    # so defaulting every request in this file to an admin token preserves
    # all prior assertions unchanged now that these endpoints require auth.
    # Role-specific behaviour (sales/reviewer) is covered in
    # tests/test_api_rbac.py.
    token = _login_as("admin")
    client.headers["Authorization"] = f"Bearer {token}"
    yield
    del client.headers["Authorization"]


def test_sales_workflow_endpoint_returns_summary():
    response = client.post(
        "/api/v1/workflows/sales",
        json={
            "company_name": "Acme GmbH",
            "website_url": "https://acme.example.com",
            "industry": "Logistics",
            "location": "Berlin",
            "company_description": "A logistics provider.",
            "website_text": "We move freight across Europe.",
            "target_persona": "Head of Operations",
            "product_or_service_offered": "Freight visibility platform",
            "sender_name": "John Smith",
            "sender_company": "Beta Vertrieb GmbH",
            "tone": "consultative",
            "language": "English",
            "notes": "Met at trade fair.",
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "completed"
    assert data["company_name"] == "Acme GmbH"
    assert data["human_review_required"] is True
    assert isinstance(data["workflow_id"], str) and data["workflow_id"]

    for step in ("lead_research", "company_intelligence", "personalization", "email_draft"):
        assert step in data
        assert data[step]["company_name"] == "Acme GmbH"

    # review_checklist and compliance_notes are always populated by the
    # workflow itself; missing_information depends on what the (mock)
    # provider reports and may legitimately be empty.
    assert isinstance(data["missing_information"], list)
    for list_field in ("review_checklist", "compliance_notes"):
        assert isinstance(data[list_field], list)
        assert len(data[list_field]) > 0

    assert 0.0 <= data["confidence_score"] <= 1.0
    assert any("no email was sent" in note.lower() for note in data["compliance_notes"])


def test_sales_workflow_endpoint_requires_company_name():
    response = client.post(
        "/api/v1/workflows/sales",
        json={"product_or_service_offered": "Freight API"},
    )
    assert response.status_code == 422


def test_sales_workflow_endpoint_requires_product_or_service_offered():
    response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH"},
    )
    assert response.status_code == 422


def test_sales_workflow_endpoint_rejects_empty_company_name():
    response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "   ", "product_or_service_offered": "Freight API"},
    )
    assert response.status_code == 422


def test_sales_workflow_endpoint_rejects_invalid_url():
    response = client.post(
        "/api/v1/workflows/sales",
        json={
            "company_name": "Acme GmbH",
            "product_or_service_offered": "Freight API",
            "website_url": "not-a-url",
        },
    )
    assert response.status_code == 422


def test_sales_workflow_endpoint_rejects_invalid_tone():
    response = client.post(
        "/api/v1/workflows/sales",
        json={
            "company_name": "Acme GmbH",
            "product_or_service_offered": "Freight API",
            "tone": "aggressive",
        },
    )
    assert response.status_code == 422


def test_sales_workflow_endpoint_uses_minimal_defaults():
    response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    )
    assert response.status_code == 200
    assert response.json()["company_name"] == "Acme GmbH"


# -- CRM integration: company/lead/contact/email draft/interaction sync ----

def test_sales_workflow_endpoint_creates_company_and_lead():
    response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["crm_company_id"]
    assert data["crm_lead_id"]
    assert data["crm_email_draft_id"]

    companies = client.get("/api/v1/companies").json()
    assert any(company["id"] == data["crm_company_id"] for company in companies)

    leads = client.get("/api/v1/leads").json()
    assert any(lead["id"] == data["crm_lead_id"] for lead in leads)


def test_sales_workflow_endpoint_reuses_company_and_lead_on_second_run():
    first = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    ).json()
    second = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    ).json()

    assert first["crm_company_id"] == second["crm_company_id"]
    assert first["crm_lead_id"] == second["crm_lead_id"]
    assert len(client.get("/api/v1/companies").json()) == 1
    assert len(client.get("/api/v1/leads").json()) == 1


def test_sales_workflow_endpoint_creates_contact_when_recipient_name_given():
    response = client.post(
        "/api/v1/workflows/sales",
        json={
            "company_name": "Acme GmbH",
            "product_or_service_offered": "Freight API",
            "recipient_name": "Jane Doe",
        },
    ).json()

    contacts = client.get("/api/v1/contacts").json()
    assert len(contacts) == 1
    assert contacts[0]["first_name"] == "Jane"
    assert contacts[0]["last_name"] == "Doe"
    assert contacts[0]["company_id"] == response["crm_company_id"]


def test_sales_workflow_endpoint_saves_email_draft_only():
    response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    ).json()

    drafts = client.get("/api/v1/email-drafts").json()
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft["id"] == response["crm_email_draft_id"]
    assert draft["status"] == "draft"
    assert draft["company_id"] == response["crm_company_id"]
    # No field on the saved draft ever represents that the email was sent.
    assert "sent" not in draft
    assert "sent_at" not in draft


def test_sales_workflow_endpoint_records_an_interaction():
    client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    )

    interactions = client.get("/api/v1/interactions").json()
    assert len(interactions) == 1
    interaction = interactions[0]
    assert interaction["type"] == "workflow_run"
    assert interaction["status"] == "draft_created"
    assert "no email was sent" in interaction["notes"].lower()


def test_sales_workflow_run_detail_includes_crm_links():
    response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    ).json()

    run_detail = client.get(f"/api/v1/workflows/sales/runs/{response['workflow_id']}").json()
    assert run_detail["company_id"] == response["crm_company_id"]
    assert run_detail["lead_id"] == response["crm_lead_id"]
    assert run_detail["email_draft_id"] == response["crm_email_draft_id"]


def test_get_sales_workflow_crm_links_endpoint():
    response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    ).json()

    links_response = client.get(
        f"/api/v1/workflows/sales/runs/{response['workflow_id']}/crm-links"
    )

    assert links_response.status_code == 200
    links = links_response.json()
    assert links["workflow_id"] == response["workflow_id"]
    assert links["company_id"] == response["crm_company_id"]
    assert links["lead_id"] == response["crm_lead_id"]
    assert links["email_draft_id"] == response["crm_email_draft_id"]
    assert links["contact_id"] is None


def test_get_sales_workflow_crm_links_returns_404_for_unknown_id():
    response = client.get(
        "/api/v1/workflows/sales/runs/00000000-0000-0000-0000-000000000000/crm-links"
    )
    assert response.status_code == 404


# -- workflow history: persistence, listing, retrieval, review status ------

def test_sales_workflow_endpoint_persists_a_run():
    response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    )
    workflow_id = response.json()["workflow_id"]

    run_response = client.get(f"/api/v1/workflows/sales/runs/{workflow_id}")

    assert run_response.status_code == 200
    run_data = run_response.json()
    assert run_data["id"] == workflow_id
    assert run_data["company_name"] == "Acme GmbH"
    assert run_data["status"] == "completed"
    assert run_data["review_status"] == "needs_review"
    assert run_data["result_payload"]["company_name"] == "Acme GmbH"
    assert run_data["input_payload"]["company_name"] == "Acme GmbH"


def test_get_sales_workflow_run_returns_404_for_unknown_id():
    response = client.get(
        "/api/v1/workflows/sales/runs/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


def test_list_sales_workflow_runs_returns_created_runs():
    client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    )
    client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Globex Inc", "product_or_service_offered": "Widgets"},
    )

    response = client.get("/api/v1/workflows/sales/runs")

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 100
    assert data["offset"] == 0
    assert len(data["items"]) == 2
    company_names = {item["company_name"] for item in data["items"]}
    assert company_names == {"Acme GmbH", "Globex Inc"}


def test_list_sales_workflow_runs_filters_by_company_name():
    client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    )
    client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Globex Inc", "product_or_service_offered": "Widgets"},
    )

    response = client.get("/api/v1/workflows/sales/runs", params={"company_name": "globex"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["company_name"] == "Globex Inc"


def test_update_review_status_changes_status_and_never_sends_anything():
    post_response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    )
    workflow_id = post_response.json()["workflow_id"]

    patch_response = client.patch(
        f"/api/v1/workflows/sales/runs/{workflow_id}/review-status",
        json={"review_status": "approved"},
    )

    assert patch_response.status_code == 200
    data = patch_response.json()
    assert data["review_status"] == "approved"
    # Approval is an internal marker only — the response never carries a
    # "sent" / "contacted" flag, and this endpoint has no side effect beyond
    # updating review_status.
    assert "sent" not in data
    assert "contacted" not in data

    get_response = client.get(f"/api/v1/workflows/sales/runs/{workflow_id}")
    assert get_response.json()["review_status"] == "approved"


async def test_update_review_status_approved_mirrors_onto_lead_pipeline_status(
    _fake_crm_repositories,
):
    post_response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    )
    data = post_response.json()
    workflow_id = data["workflow_id"]
    lead_id = data["crm_lead_id"]

    patch_response = client.patch(
        f"/api/v1/workflows/sales/runs/{workflow_id}/review-status",
        json={"review_status": "approved"},
    )
    assert patch_response.status_code == 200

    leads = _fake_crm_repositories[get_lead_repository]
    lead = await leads.get(uuid.UUID(lead_id))
    # Mirroring the run's approved review status onto the lead's pipeline
    # status is bookkeeping only — no email field appears anywhere on the
    # lead, and no separate "sent" action is exposed.
    assert lead.pipeline_status.value == "approved"
    assert not hasattr(lead, "sent")


def test_update_review_status_refuses_approval_for_a_run_blocked_at_creation():
    # No recipient_name given, so no Contact is created — the run's linked
    # company has no domain and no matching name either, so the ONLY place
    # the original email-based block is recorded is the run's own stored
    # result_payload. Approval must still be refused.
    create_response = client.post(
        "/api/v1/compliance/do-not-contact",
        json={"email": "blocked@example.com", "reason": "Opt-out"},
    )
    assert create_response.status_code == 201

    post_response = client.post(
        "/api/v1/workflows/sales",
        json={
            "company_name": "Blocked Recipient GmbH",
            "product_or_service_offered": "Freight API",
            "recipient_email": "blocked@example.com",
        },
    )
    assert post_response.status_code == 200
    data = post_response.json()
    assert data["status"] == "blocked"
    workflow_id = data["workflow_id"]

    patch_response = client.patch(
        f"/api/v1/workflows/sales/runs/{workflow_id}/review-status",
        json={"review_status": "approved"},
    )

    assert patch_response.status_code == 409
    assert "do-not-contact" in patch_response.json()["detail"].lower()

    get_response = client.get(f"/api/v1/workflows/sales/runs/{workflow_id}")
    assert get_response.json()["review_status"] == "needs_review"


def test_update_review_status_rejects_invalid_value():
    post_response = client.post(
        "/api/v1/workflows/sales",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    )
    workflow_id = post_response.json()["workflow_id"]

    response = client.patch(
        f"/api/v1/workflows/sales/runs/{workflow_id}/review-status",
        json={"review_status": "sent"},
    )
    assert response.status_code == 422


def test_update_review_status_returns_404_for_unknown_id():
    response = client.patch(
        "/api/v1/workflows/sales/runs/00000000-0000-0000-0000-000000000000/review-status",
        json={"review_status": "approved"},
    )
    assert response.status_code == 404


# -- website research integration -------------------------------------------

class _FakeWebsiteResearchService:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error

    async def research(self, request):
        if self._error is not None:
            raise self._error
        return self._result


def _fake_website_research_result() -> WebsiteResearchResponse:
    return WebsiteResearchResponse(
        url="https://acme.example.com",
        final_url="https://acme.example.com",
        domain="acme.example.com",
        title="Acme GmbH",
        meta_description=None,
        extracted_text="Acme builds freight visibility software.",
        text_length=42,
        pages_fetched=1,
        sources_used=["https://acme.example.com"],
        warnings=[],
    )


def test_sales_workflow_with_use_website_research_true_succeeds():
    app.dependency_overrides[get_website_research_service] = _returning(
        _FakeWebsiteResearchService(result=_fake_website_research_result())
    )
    try:
        response = client.post(
            "/api/v1/workflows/sales",
            json={
                "company_name": "Acme GmbH",
                "product_or_service_offered": "Freight API",
                "website_url": "https://acme.example.com",
                "use_website_research": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_website_research_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["website_research_used"] is True
    assert data["website_research"]["domain"] == "acme.example.com"
    assert data["website_research_warnings"] == []


def test_sales_workflow_with_blocked_website_url_returns_clean_400():
    app.dependency_overrides[get_website_research_service] = _returning(
        _FakeWebsiteResearchService(
            error=InvalidWebsiteURLError("Host 'localhost' is not allowed.")
        )
    )
    try:
        response = client.post(
            "/api/v1/workflows/sales",
            json={
                "company_name": "Acme GmbH",
                "product_or_service_offered": "Freight API",
                "website_url": "http://localhost/",
                "use_website_research": True,
            },
        )
    finally:
        app.dependency_overrides.pop(get_website_research_service, None)

    assert response.status_code == 400
    detail = response.json()["detail"]
    # No internal validation detail (e.g. the specific blocked host) leaks
    # into the client-facing error message.
    assert "localhost" not in detail
    assert "is not allowed" not in detail


def test_research_website_endpoint_still_works_alongside_sales_workflow():
    app.dependency_overrides[get_website_research_service] = _returning(
        _FakeWebsiteResearchService(result=_fake_website_research_result())
    )
    try:
        response = client.post(
            "/api/v1/research/website", json={"url": "https://acme.example.com"}
        )
    finally:
        app.dependency_overrides.pop(get_website_research_service, None)

    assert response.status_code == 200
    assert response.json()["domain"] == "acme.example.com"


# -- regression: existing routes remain intact ----------------------------

def test_health_endpoint_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/health" in paths


def test_all_agent_endpoints_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/agents/demo" in paths
    assert "/api/v1/agents/lead-research" in paths
    assert "/api/v1/agents/company-intelligence" in paths
    assert "/api/v1/agents/personalization" in paths
    assert "/api/v1/agents/email-draft" in paths
    assert "/api/v1/agents/reply-analysis" in paths
    assert "/api/v1/workflows/sales" in paths
    assert "/api/v1/workflows/sales/runs" in paths
    assert "/api/v1/workflows/sales/runs/{workflow_id}" in paths
    assert "/api/v1/workflows/sales/runs/{workflow_id}/review-status" in paths
    assert "/api/v1/workflows/sales/runs/{workflow_id}/crm-links" in paths


def test_all_crm_endpoints_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/companies" in paths
    assert "/api/v1/leads" in paths
    assert "/api/v1/leads/{lead_id}" in paths
    assert "/api/v1/contacts" in paths
    assert "/api/v1/interactions" in paths
    assert "/api/v1/email-drafts" in paths


def test_lead_research_endpoint_still_works():
    response = client.post(
        "/api/v1/agents/lead-research",
        json={"company_name": "Acme GmbH"},
    )
    assert response.status_code == 200
    assert response.json()["company_name"] == "Acme GmbH"


def test_company_intelligence_endpoint_still_works():
    response = client.post(
        "/api/v1/agents/company-intelligence",
        json={"company_name": "Acme GmbH"},
    )
    assert response.status_code == 200
    assert response.json()["company_name"] == "Acme GmbH"


def test_personalization_endpoint_still_works():
    response = client.post(
        "/api/v1/agents/personalization",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    )
    assert response.status_code == 200
    assert response.json()["company_name"] == "Acme GmbH"


def test_email_draft_endpoint_still_works():
    response = client.post(
        "/api/v1/agents/email-draft",
        json={"company_name": "Acme GmbH", "product_or_service_offered": "Freight API"},
    )
    assert response.status_code == 200
    assert response.json()["company_name"] == "Acme GmbH"


def test_reply_analysis_endpoint_still_works():
    response = client.post(
        "/api/v1/agents/reply-analysis",
        json={"company_name": "Acme GmbH", "reply_text": "Sounds interesting."},
    )
    assert response.status_code == 200
    assert response.json()["company_name"] == "Acme GmbH"
