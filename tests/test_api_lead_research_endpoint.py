from fastapi.testclient import TestClient

from backend.main import app

# No context manager → lifespan (and thus DB init) does not run; the
# lead-research endpoint uses the mock LLM provider and touches no external
# services.
client = TestClient(app)


def test_lead_research_endpoint_returns_profile():
    response = client.post(
        "/api/v1/agents/lead-research",
        json={
            "company_name": "Acme GmbH",
            "website_url": "https://acme.example.com",
            "industry": "Logistics",
            "location": "Berlin",
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
    assert isinstance(data["short_summary"], str)
    assert isinstance(data["target_customers"], list)
    assert isinstance(data["likely_pain_points"], list)
    assert isinstance(data["possible_sales_angles"], list)
    assert isinstance(data["missing_information"], list)
    assert isinstance(data["sources_used"], list)
    assert 0.0 <= data["confidence_score"] <= 1.0


def test_lead_research_endpoint_requires_company_name():
    response = client.post("/api/v1/agents/lead-research", json={})
    assert response.status_code == 422


def test_lead_research_endpoint_rejects_empty_company_name():
    response = client.post(
        "/api/v1/agents/lead-research", json={"company_name": "   "}
    )
    assert response.status_code == 422


def test_lead_research_endpoint_rejects_invalid_url():
    response = client.post(
        "/api/v1/agents/lead-research",
        json={"company_name": "Acme GmbH", "website_url": "not-a-url"},
    )
    assert response.status_code == 422


def test_health_endpoint_still_registered():
    # Guard against breaking existing routes when extending the router.
    paths = {route.path for route in app.routes}
    assert "/api/v1/health" in paths
    assert "/api/v1/agents/demo" in paths
    assert "/api/v1/agents/lead-research" in paths
