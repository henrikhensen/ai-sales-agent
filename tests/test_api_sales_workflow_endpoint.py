import pytest
from fastapi.testclient import TestClient

from backend.api.v1.dependencies import (
    get_company_repository,
    get_contact_repository,
    get_email_draft_repository,
    get_interaction_repository,
    get_lead_repository,
    get_workflow_run_repository,
)
from backend.main import app
from tests.conftest import (
    FakeCompanyRepository,
    FakeContactRepository,
    FakeEmailDraftRepository,
    FakeInteractionRepository,
    FakeLeadRepository,
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
    }
    for dependency, fake in fakes.items():
        app.dependency_overrides[dependency] = _returning(fake)
    yield fakes
    for dependency in fakes:
        app.dependency_overrides.pop(dependency, None)


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
