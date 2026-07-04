from fastapi.testclient import TestClient

from backend.main import app

# No context manager → lifespan (and thus DB init) does not run; the sales
# workflow only calls the existing agent services with the mock LLM provider
# and touches no external services.
client = TestClient(app)


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
