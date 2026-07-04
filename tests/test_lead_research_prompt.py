from backend.agents.lead_research.prompt import (
    LEAD_RESEARCH_SYSTEM_PROMPT,
    build_lead_research_prompt,
)
from backend.agents.lead_research.schemas import LeadResearchRequest


def test_system_prompt_enforces_compliance_rules():
    prompt = LEAD_RESEARCH_SYSTEM_PROMPT.lower()

    assert "valid json" in prompt
    assert "do not invent" in prompt
    assert "missing_information" in prompt
    assert "confidence_score" in prompt
    assert "sources_used" in prompt
    # Analysis only — never propose outreach.
    assert "never propose" in prompt


def test_build_prompt_includes_supplied_fields():
    request = LeadResearchRequest(
        company_name="Acme GmbH",
        website_url="https://acme.example.com",
        industry="Logistics",
        location="Berlin",
        notes="Met at trade fair.",
    )

    prompt = build_lead_research_prompt(request)

    assert "Acme GmbH" in prompt
    assert "https://acme.example.com" in prompt
    assert "Logistics" in prompt
    assert "Berlin" in prompt
    assert "Met at trade fair." in prompt


def test_build_prompt_marks_missing_optional_fields():
    request = LeadResearchRequest(company_name="Acme GmbH")

    prompt = build_lead_research_prompt(request)

    assert "Acme GmbH" in prompt
    # Optional fields that were not supplied are explicitly flagged.
    assert prompt.count("not provided") == 4
