from fastapi.testclient import TestClient

from backend.main import app

# No context manager → lifespan (and thus DB init) does not run; the
# company-intelligence endpoint uses the mock LLM provider and touches no
# external services.
client = TestClient(app)


def test_company_intelligence_endpoint_returns_profile():
    response = client.post(
        "/api/v1/agents/company-intelligence",
        json={
            "company_name": "Acme GmbH",
            "website_url": "https://acme.example.com",
            "industry": "Logistics",
            "location": "Berlin",
            "company_description": "A logistics provider.",
            "known_products": ["Freight API", "Tracking"],
            "known_customers": ["Beta AG"],
            "notes": "Met at trade fair.",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Identity fields echo the validated input.
    assert data["company_name"] == "Acme GmbH"
    assert data["website_url"] == "https://acme.example.com/"
    assert data["industry"] == "Logistics"
    assert data["location"] == "Berlin"

    # Structured profile fields are present with the right shapes.
    assert isinstance(data["business_summary"], str)
    assert isinstance(data["positioning_summary"], str)
    for list_field in (
        "products_and_services",
        "target_segments",
        "likely_buyer_personas",
        "value_proposition",
        "possible_competitive_context",
        "sales_relevance",
        "potential_business_challenges",
        "personalization_hooks",
        "missing_information",
        "sources_used",
    ):
        assert isinstance(data[list_field], list)
    assert 0.0 <= data["confidence_score"] <= 1.0


def test_company_intelligence_endpoint_requires_company_name():
    response = client.post("/api/v1/agents/company-intelligence", json={})
    assert response.status_code == 422


def test_company_intelligence_endpoint_rejects_empty_company_name():
    response = client.post(
        "/api/v1/agents/company-intelligence", json={"company_name": "   "}
    )
    assert response.status_code == 422


def test_company_intelligence_endpoint_rejects_invalid_url():
    response = client.post(
        "/api/v1/agents/company-intelligence",
        json={"company_name": "Acme GmbH", "website_url": "not-a-url"},
    )
    assert response.status_code == 422


def test_company_intelligence_endpoint_rejects_empty_list_item():
    response = client.post(
        "/api/v1/agents/company-intelligence",
        json={"company_name": "Acme GmbH", "known_products": ["Valid", "  "]},
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


def test_lead_research_endpoint_still_works():
    # The previously shipped agent must keep functioning end-to-end.
    response = client.post(
        "/api/v1/agents/lead-research",
        json={"company_name": "Acme GmbH"},
    )
    assert response.status_code == 200
    assert response.json()["company_name"] == "Acme GmbH"
