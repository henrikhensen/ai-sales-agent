import pytest
from pydantic import ValidationError

from backend.agents.email_draft.schemas import EmailDraftRequest, EmailDraftResponse


# -- EmailDraftRequest ------------------------------------------------------

def test_request_accepts_minimal_valid_input():
    request = EmailDraftRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    assert request.company_name == "Acme GmbH"
    assert request.product_or_service_offered == "Freight API"
    assert request.website_url is None
    assert request.relevant_observations is None
    assert request.language == "German"


def test_request_accepts_full_valid_input():
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

    assert str(request.website_url) == "https://acme.example.com/"
    assert request.recipient_name == "Jane Doe"
    assert request.tone == "consultative"
    assert request.language == "English"


def test_request_requires_company_name():
    with pytest.raises(ValidationError):
        EmailDraftRequest(product_or_service_offered="Freight API")


def test_request_requires_product_or_service_offered():
    with pytest.raises(ValidationError):
        EmailDraftRequest(company_name="Acme GmbH")


def test_request_rejects_empty_company_name():
    with pytest.raises(ValidationError):
        EmailDraftRequest(company_name="", product_or_service_offered="Freight API")


def test_request_rejects_whitespace_only_product_or_service_offered():
    with pytest.raises(ValidationError):
        EmailDraftRequest(company_name="Acme GmbH", product_or_service_offered="   ")


def test_request_trims_string_fields():
    request = EmailDraftRequest(
        company_name="  Acme GmbH  ",
        product_or_service_offered="  Freight API  ",
        recipient_name="  Jane Doe  ",
    )
    assert request.company_name == "Acme GmbH"
    assert request.product_or_service_offered == "Freight API"
    assert request.recipient_name == "Jane Doe"


def test_request_rejects_empty_optional_string():
    with pytest.raises(ValidationError):
        EmailDraftRequest(
            company_name="Acme", product_or_service_offered="Freight API", notes=""
        )


def test_request_rejects_invalid_website_url():
    with pytest.raises(ValidationError):
        EmailDraftRequest(
            company_name="Acme",
            product_or_service_offered="Freight API",
            website_url="not-a-url",
        )


def test_request_rejects_empty_string_in_list():
    with pytest.raises(ValidationError):
        EmailDraftRequest(
            company_name="Acme",
            product_or_service_offered="Freight API",
            pain_point_angles=["Valid", "  "],
        )


def test_request_trims_list_items():
    request = EmailDraftRequest(
        company_name="Acme",
        product_or_service_offered="Freight API",
        suggested_ctas=["  Book a call  "],
    )
    assert request.suggested_ctas == ["Book a call"]


def test_request_rejects_invalid_tone():
    with pytest.raises(ValidationError):
        EmailDraftRequest(
            company_name="Acme",
            product_or_service_offered="Freight API",
            tone="aggressive",
        )


def test_request_accepts_valid_tones():
    for tone in ("professional", "friendly", "concise", "consultative"):
        request = EmailDraftRequest(
            company_name="Acme", product_or_service_offered="Freight API", tone=tone
        )
        assert request.tone == tone


# -- EmailDraftResponse -------------------------------------------------------

def _valid_response_kwargs() -> dict:
    return {
        "company_name": "Acme GmbH",
        "email_body": "Dear Jane, ...",
        "confidence_score": 0.5,
    }


def test_response_accepts_valid_payload():
    response = EmailDraftResponse(**_valid_response_kwargs())

    assert response.company_name == "Acme GmbH"
    assert response.confidence_score == 0.5
    assert response.subject_lines == []
    assert response.alternative_openings == []
    assert response.alternative_ctas == []
    assert response.claims_to_verify == []
    assert response.do_not_send_if == []
    assert response.compliance_notes == []
    assert response.missing_information == []


def test_response_clamps_confidence_above_one():
    response = EmailDraftResponse(
        **{**_valid_response_kwargs(), "confidence_score": 4.2}
    )
    assert response.confidence_score == 1.0


def test_response_clamps_confidence_below_zero():
    response = EmailDraftResponse(
        **{**_valid_response_kwargs(), "confidence_score": -1.0}
    )
    assert response.confidence_score == 0.0


def test_response_rejects_non_numeric_confidence():
    with pytest.raises(ValidationError):
        EmailDraftResponse(
            **{**_valid_response_kwargs(), "confidence_score": "high"}
        )


def test_response_requires_email_body():
    with pytest.raises(ValidationError):
        EmailDraftResponse(company_name="Acme", confidence_score=0.5)
