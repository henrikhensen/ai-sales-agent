from backend.agents.company_intelligence.prompt import (
    COMPANY_INTELLIGENCE_SYSTEM_PROMPT,
    build_company_intelligence_prompt,
)
from backend.agents.company_intelligence.schemas import CompanyIntelligenceRequest


def test_system_prompt_enforces_compliance_rules():
    prompt = COMPANY_INTELLIGENCE_SYSTEM_PROMPT.lower()

    assert "valid json" in prompt
    assert "do not invent facts" in prompt
    assert "do not invent competitors" in prompt
    assert "missing_information" in prompt
    assert "confidence_score" in prompt
    assert "sources_used" in prompt
    assert "personalization_hooks" in prompt
    # Analysis only — never propose outreach.
    assert "analysis only" in prompt


def test_build_prompt_includes_supplied_fields():
    request = CompanyIntelligenceRequest(
        company_name="Acme GmbH",
        website_url="https://acme.example.com",
        industry="Logistics",
        location="Berlin",
        company_description="A logistics provider.",
        website_text="We move freight across Europe.",
        known_products=["Freight API", "Tracking"],
        known_customers=["Beta AG"],
        notes="Met at trade fair.",
    )

    prompt = build_company_intelligence_prompt(request)

    assert "Acme GmbH" in prompt
    assert "https://acme.example.com" in prompt
    assert "Logistics" in prompt
    assert "Berlin" in prompt
    assert "A logistics provider." in prompt
    assert "We move freight across Europe." in prompt
    assert "Freight API, Tracking" in prompt
    assert "Beta AG" in prompt
    assert "Met at trade fair." in prompt


def test_build_prompt_marks_missing_optional_fields():
    request = CompanyIntelligenceRequest(company_name="Acme GmbH")

    prompt = build_company_intelligence_prompt(request)

    assert "Acme GmbH" in prompt
    # 8 optional fields (website, industry, location, description, website_text,
    # known_products, known_customers, notes) are all flagged as not provided.
    assert prompt.count("not provided") == 8
