from backend.agents.personalization.prompt import (
    PERSONALIZATION_SYSTEM_PROMPT,
    build_personalization_prompt,
)
from backend.agents.personalization.schemas import PersonalizationRequest


def test_system_prompt_enforces_compliance_rules():
    prompt = PERSONALIZATION_SYSTEM_PROMPT.lower()

    assert "valid json" in prompt
    assert "do not invent facts" in prompt
    assert "missing_information" in prompt
    assert "confidence_score" in prompt
    assert "sources_used" in prompt
    assert "do_not_use_claims" in prompt
    assert "suggested_ctas" in prompt
    assert "ready-to-send email" in prompt
    assert "aggressive" in prompt
    # Strategy only — never propose or send outreach.
    assert "never draft, schedule, or send any" in prompt


def test_build_prompt_includes_supplied_fields():
    request = PersonalizationRequest(
        company_name="Acme GmbH",
        website_url="https://acme.example.com",
        industry="Logistics",
        location="Berlin",
        lead_summary="Logistics company based in Berlin.",
        company_intelligence_summary="Mid-market freight carrier.",
        target_persona="Head of Operations",
        product_or_service_offered="Freight visibility platform",
        value_proposition="Real-time shipment tracking.",
        known_pain_points=["Lack of shipment visibility"],
        known_triggers=["Recent expansion into new markets"],
        notes="Met at trade fair.",
    )

    prompt = build_personalization_prompt(request)

    assert "Acme GmbH" in prompt
    assert "https://acme.example.com" in prompt
    assert "Logistics" in prompt
    assert "Berlin" in prompt
    assert "Logistics company based in Berlin." in prompt
    assert "Mid-market freight carrier." in prompt
    assert "Head of Operations" in prompt
    assert "Freight visibility platform" in prompt
    assert "Real-time shipment tracking." in prompt
    assert "Lack of shipment visibility" in prompt
    assert "Recent expansion into new markets" in prompt
    assert "Met at trade fair." in prompt


def test_build_prompt_marks_missing_optional_fields():
    request = PersonalizationRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    prompt = build_personalization_prompt(request)

    assert "Acme GmbH" in prompt
    # 10 optional fields (website, industry, location, lead_summary,
    # company_intelligence_summary, target_persona, value_proposition,
    # known_pain_points, known_triggers, notes) are all flagged as not provided.
    assert prompt.count("not provided") == 10
