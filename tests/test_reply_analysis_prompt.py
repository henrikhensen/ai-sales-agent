from backend.agents.reply_analysis.prompt import (
    REPLY_ANALYSIS_SYSTEM_PROMPT,
    build_reply_analysis_prompt,
)
from backend.agents.reply_analysis.schemas import ReplyAnalysisRequest


def test_system_prompt_enforces_compliance_rules():
    prompt = REPLY_ANALYSIS_SYSTEM_PROMPT.lower()

    assert "valid json" in prompt
    assert "classify the reply objectively" in prompt
    assert "do not invent facts" in prompt
    assert "do not invent meetings" in prompt
    assert "respect it" in prompt
    assert "never an aggressive or repeated follow-up" in prompt
    assert "draft only" in prompt
    assert "do_not_continue_if" in prompt
    assert "compliance_notes" in prompt
    assert "missing_information" in prompt
    assert "confidence_score" in prompt
    assert "unclear" in prompt


def test_build_prompt_includes_supplied_fields():
    request = ReplyAnalysisRequest(
        company_name="Acme GmbH",
        lead_name="Jane Doe",
        lead_role="Head of Operations",
        original_email_subject="Mehr Transparenz in Ihrer Sendungslogistik",
        original_email_body="Hallo Frau Doe, ...",
        reply_text="Können wir nächste Woche telefonieren?",
        previous_context="Erstkontakt vor zwei Wochen.",
        product_or_service_offered="Freight visibility platform",
        notes="Wirkt interessiert.",
    )

    prompt = build_reply_analysis_prompt(request)

    assert "Acme GmbH" in prompt
    assert "Jane Doe" in prompt
    assert "Head of Operations" in prompt
    assert "Mehr Transparenz in Ihrer Sendungslogistik" in prompt
    assert "Hallo Frau Doe, ..." in prompt
    assert "Können wir nächste Woche telefonieren?" in prompt
    assert "Erstkontakt vor zwei Wochen." in prompt
    assert "Freight visibility platform" in prompt
    assert "Wirkt interessiert." in prompt


def test_build_prompt_marks_missing_optional_fields():
    request = ReplyAnalysisRequest(
        company_name="Acme GmbH", reply_text="Not interested, please stop."
    )

    prompt = build_reply_analysis_prompt(request)

    assert "Acme GmbH" in prompt
    # 7 optional fields (lead_name, lead_role, original_email_subject,
    # original_email_body, previous_context, product_or_service_offered,
    # notes) are all flagged as not provided.
    assert prompt.count("not provided") == 7
