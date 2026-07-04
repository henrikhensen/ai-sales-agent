from fastapi.testclient import TestClient

from backend.main import app

# No context manager → lifespan (and thus DB init) does not run; the
# personalization endpoint uses the mock LLM provider and touches no external
# services.
client = TestClient(app)


def test_personalization_endpoint_returns_strategy():
    response = client.post(
        "/api/v1/agents/personalization",
        json={
            "company_name": "Acme GmbH",
            "website_url": "https://acme.example.com",
            "industry": "Logistics",
            "location": "Berlin",
            "lead_summary": "Logistics company based in Berlin.",
            "company_intelligence_summary": "Mid-market freight carrier.",
            "target_persona": "Head of Operations",
            "product_or_service_offered": "Freight visibility platform",
            "value_proposition": "Real-time shipment tracking.",
            "known_pain_points": ["Lack of shipment visibility"],
            "known_triggers": ["Recent expansion into new markets"],
            "notes": "Met at trade fair.",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Identity fields echo the validated input.
    assert data["company_name"] == "Acme GmbH"
    assert data["website_url"] == "https://acme.example.com/"
    assert data["industry"] == "Logistics"

    # Structured strategy fields are present with the right shapes.
    assert isinstance(data["personalization_summary"], str)
    for list_field in (
        "relevant_observations",
        "possible_conversation_starters",
        "pain_point_angles",
        "value_arguments",
        "credibility_points",
        "objection_risks",
        "suggested_ctas",
        "do_not_use_claims",
        "missing_information",
        "sources_used",
    ):
        assert isinstance(data[list_field], list)
    assert 0.0 <= data["confidence_score"] <= 1.0


def test_personalization_endpoint_requires_company_name():
    response = client.post(
        "/api/v1/agents/personalization",
        json={"product_or_service_offered": "Freight API"},
    )
    assert response.status_code == 422


def test_personalization_endpoint_requires_product_or_service_offered():
    response = client.post(
        "/api/v1/agents/personalization",
        json={"company_name": "Acme GmbH"},
    )
    assert response.status_code == 422


def test_personalization_endpoint_rejects_empty_company_name():
    response = client.post(
        "/api/v1/agents/personalization",
        json={"company_name": "   ", "product_or_service_offered": "Freight API"},
    )
    assert response.status_code == 422


def test_personalization_endpoint_rejects_invalid_url():
    response = client.post(
        "/api/v1/agents/personalization",
        json={
            "company_name": "Acme GmbH",
            "product_or_service_offered": "Freight API",
            "website_url": "not-a-url",
        },
    )
    assert response.status_code == 422


def test_personalization_endpoint_rejects_empty_list_item():
    response = client.post(
        "/api/v1/agents/personalization",
        json={
            "company_name": "Acme GmbH",
            "product_or_service_offered": "Freight API",
            "known_pain_points": ["Valid", "  "],
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
