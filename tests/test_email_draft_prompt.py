from backend.agents.email_draft.prompt import (
    EMAIL_DRAFT_SYSTEM_PROMPT,
    build_email_draft_prompt,
)
from backend.agents.email_draft.schemas import EmailDraftRequest


def test_system_prompt_enforces_compliance_rules():
    prompt = EMAIL_DRAFT_SYSTEM_PROMPT.lower()

    assert "valid json" in prompt
    assert "draft only" in prompt
    assert "never send" in prompt
    assert "do not invent facts" in prompt
    assert "missing_information" in prompt
    assert "claims_to_verify" in prompt
    assert "do_not_send_if" in prompt
    assert "compliance_notes" in prompt
    assert "false urgency" in prompt
    assert "deception" in prompt
    assert "mass-email" in prompt
    assert "confidence_score" in prompt


def test_build_prompt_includes_supplied_fields():
    request = EmailDraftRequest(
        company_name="Acme GmbH",
        website_url="https://acme.example.com",
        industry="Logistics",
        recipient_role="Head of Operations",
        recipient_name="Jane Doe",
        sender_name="John Smith",
        sender_company="Beta Vertrieb GmbH",
        product_or_service_offered="Freight visibility platform",
        personalization_summary="Focus on operational efficiency gains.",
        relevant_observations=["Recent expansion into new markets"],
        pain_point_angles=["Lack of shipment visibility"],
        value_arguments=["Real-time tracking reduces manual follow-ups"],
        credibility_points=["Works with mid-market freight carriers"],
        suggested_ctas=["Propose a 15-minute discovery call"],
        tone="consultative",
        language="English",
        notes="Met at trade fair.",
    )

    prompt = build_email_draft_prompt(request)

    assert "Acme GmbH" in prompt
    assert "https://acme.example.com" in prompt
    assert "Logistics" in prompt
    assert "Head of Operations" in prompt
    assert "Jane Doe" in prompt
    assert "John Smith" in prompt
    assert "Beta Vertrieb GmbH" in prompt
    assert "Freight visibility platform" in prompt
    assert "Focus on operational efficiency gains." in prompt
    assert "Recent expansion into new markets" in prompt
    assert "Lack of shipment visibility" in prompt
    assert "Real-time tracking reduces manual follow-ups" in prompt
    assert "Works with mid-market freight carriers" in prompt
    assert "Propose a 15-minute discovery call" in prompt
    assert "consultative" in prompt
    assert "English" in prompt
    assert "Met at trade fair." in prompt


def test_build_prompt_marks_missing_optional_fields():
    request = EmailDraftRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    prompt = build_email_draft_prompt(request)

    assert "Acme GmbH" in prompt
    # 14 optional fields (website, industry, recipient_role, recipient_name,
    # sender_name, sender_company, personalization_summary,
    # relevant_observations, pain_point_angles, value_arguments,
    # credibility_points, suggested_ctas, tone, notes) are flagged as not
    # provided. `language` defaults to "German" and is therefore always set.
    assert prompt.count("not provided") == 14
    assert "German" in prompt
