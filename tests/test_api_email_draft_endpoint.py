from fastapi.testclient import TestClient

from backend.main import app

# No context manager → lifespan (and thus DB init) does not run; the
# email-draft endpoint uses the mock LLM provider and touches no external
# services.
client = TestClient(app)


def test_email_draft_endpoint_returns_draft():
    response = client.post(
        "/api/v1/agents/email-draft",
        json={
            "company_name": "Acme GmbH",
            "website_url": "https://acme.example.com",
            "industry": "Logistics",
            "recipient_role": "Head of Operations",
            "recipient_name": "Jane Doe",
            "sender_name": "John Smith",
            "sender_company": "Beta Vertrieb GmbH",
            "product_or_service_offered": "Freight visibility platform",
            "personalization_summary": "Focus on operational efficiency gains.",
            "relevant_observations": ["Recent expansion into new markets"],
            "pain_point_angles": ["Lack of shipment visibility"],
            "value_arguments": ["Real-time tracking reduces manual follow-ups"],
            "credibility_points": ["Works with mid-market freight carriers"],
            "suggested_ctas": ["Propose a 15-minute discovery call"],
            "tone": "consultative",
            "language": "English",
            "notes": "Met at trade fair.",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Identity field echoes the validated input.
    assert data["company_name"] == "Acme GmbH"

    # Structured draft fields are present with the right shapes.
    assert isinstance(data["email_body"], str)
    for list_field in (
        "subject_lines",
        "alternative_openings",
        "alternative_ctas",
        "personalization_used",
        "claims_to_verify",
        "do_not_send_if",
        "compliance_notes",
        "missing_information",
    ):
        assert isinstance(data[list_field], list)
    assert 0.0 <= data["confidence_score"] <= 1.0


def test_email_draft_endpoint_requires_company_name():
    response = client.post(
        "/api/v1/agents/email-draft",
        json={"product_or_service_offered": "Freight API"},
    )
    assert response.status_code == 422


def test_email_draft_endpoint_requires_product_or_service_offered():
    response = client.post(
        "/api/v1/agents/email-draft",
        json={"company_name": "Acme GmbH"},
    )
    assert response.status_code == 422


def test_email_draft_endpoint_rejects_empty_company_name():
    response = client.post(
        "/api/v1/agents/email-draft",
        json={"company_name": "   ", "product_or_service_offered": "Freight API"},
    )
    assert response.status_code == 422


def test_email_draft_endpoint_rejects_invalid_url():
    response = client.post(
        "/api/v1/agents/email-draft",
        json={
            "company_name": "Acme GmbH",
            "product_or_service_offered": "Freight API",
            "website_url": "not-a-url",
        },
    )
    assert response.status_code == 422


def test_email_draft_endpoint_rejects_empty_list_item():
    response = client.post(
        "/api/v1/agents/email-draft",
        json={
            "company_name": "Acme GmbH",
            "product_or_service_offered": "Freight API",
            "pain_point_angles": ["Valid", "  "],
        },
    )
    assert response.status_code == 422


def test_email_draft_endpoint_rejects_invalid_tone():
    response = client.post(
        "/api/v1/agents/email-draft",
        json={
            "company_name": "Acme GmbH",
            "product_or_service_offered": "Freight API",
            "tone": "aggressive",
        },
    )
    assert response.status_code == 422


# -- regression: existing routes remain intact ----------------------------

def test_health_endpoint_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/health" in paths


def test_existing_agent_endpoints_still_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/agents/demo" in paths
    assert "/api/v1/agents/lead-research" in paths
    assert "/api/v1/agents/company-intelligence" in paths
    assert "/api/v1/agents/personalization" in paths
    assert "/api/v1/agents/email-draft" in paths


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
