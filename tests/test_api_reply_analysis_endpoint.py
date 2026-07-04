from fastapi.testclient import TestClient

from backend.main import app

# No context manager → lifespan (and thus DB init) does not run; the
# reply-analysis endpoint uses the mock LLM provider and touches no external
# services.
client = TestClient(app)


def test_reply_analysis_endpoint_returns_analysis():
    response = client.post(
        "/api/v1/agents/reply-analysis",
        json={
            "company_name": "Acme GmbH",
            "lead_name": "Jane Doe",
            "lead_role": "Head of Operations",
            "original_email_subject": "Mehr Transparenz in Ihrer Sendungslogistik",
            "original_email_body": "Hallo Frau Doe, ...",
            "reply_text": "Können wir nächste Woche telefonieren?",
            "previous_context": "Erstkontakt vor zwei Wochen.",
            "product_or_service_offered": "Freight visibility platform",
            "notes": "Wirkt interessiert.",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Identity field echoes the validated input.
    assert data["company_name"] == "Acme GmbH"

    # Enum fields must be valid schema values.
    assert data["classification"] in (
        "interested",
        "meeting_request",
        "question",
        "objection",
        "not_interested",
        "out_of_office",
        "unclear",
    )
    assert data["sentiment"] in ("positive", "neutral", "negative", "unclear")
    assert data["urgency"] in ("low", "medium", "high", "unclear")

    # Structured analysis fields are present with the right shapes.
    assert isinstance(data["summary"], str)
    assert isinstance(data["recommended_next_action"], str)
    for list_field in (
        "detected_intent",
        "questions_to_answer",
        "objections_detected",
        "buying_signals",
        "do_not_continue_if",
        "compliance_notes",
        "missing_information",
    ):
        assert isinstance(data[list_field], list)
    assert 0.0 <= data["confidence_score"] <= 1.0


def test_reply_analysis_endpoint_requires_company_name():
    response = client.post(
        "/api/v1/agents/reply-analysis",
        json={"reply_text": "Not interested."},
    )
    assert response.status_code == 422


def test_reply_analysis_endpoint_requires_reply_text():
    response = client.post(
        "/api/v1/agents/reply-analysis",
        json={"company_name": "Acme GmbH"},
    )
    assert response.status_code == 422


def test_reply_analysis_endpoint_rejects_empty_company_name():
    response = client.post(
        "/api/v1/agents/reply-analysis",
        json={"company_name": "   ", "reply_text": "Not interested."},
    )
    assert response.status_code == 422


def test_reply_analysis_endpoint_rejects_whitespace_only_reply_text():
    response = client.post(
        "/api/v1/agents/reply-analysis",
        json={"company_name": "Acme GmbH", "reply_text": "   "},
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
    assert "/api/v1/agents/reply-analysis" in paths


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
