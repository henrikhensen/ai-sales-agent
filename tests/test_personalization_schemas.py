import pytest
from pydantic import ValidationError

from backend.agents.personalization.schemas import (
    PersonalizationRequest,
    PersonalizationResponse,
)


# -- PersonalizationRequest ------------------------------------------------

def test_request_accepts_minimal_valid_input():
    request = PersonalizationRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    assert request.company_name == "Acme GmbH"
    assert request.product_or_service_offered == "Freight API"
    assert request.website_url is None
    assert request.known_pain_points is None
    assert request.known_triggers is None


def test_request_accepts_full_valid_input():
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

    assert str(request.website_url) == "https://acme.example.com/"
    assert request.known_pain_points == ["Lack of shipment visibility"]
    assert request.known_triggers == ["Recent expansion into new markets"]


def test_request_requires_company_name():
    with pytest.raises(ValidationError):
        PersonalizationRequest(product_or_service_offered="Freight API")


def test_request_requires_product_or_service_offered():
    with pytest.raises(ValidationError):
        PersonalizationRequest(company_name="Acme GmbH")


def test_request_rejects_empty_company_name():
    with pytest.raises(ValidationError):
        PersonalizationRequest(
            company_name="", product_or_service_offered="Freight API"
        )


def test_request_rejects_whitespace_only_product_or_service_offered():
    with pytest.raises(ValidationError):
        PersonalizationRequest(
            company_name="Acme GmbH", product_or_service_offered="   "
        )


def test_request_trims_string_fields():
    request = PersonalizationRequest(
        company_name="  Acme GmbH  ",
        product_or_service_offered="  Freight API  ",
        industry="  Logistics  ",
    )
    assert request.company_name == "Acme GmbH"
    assert request.product_or_service_offered == "Freight API"
    assert request.industry == "Logistics"


def test_request_rejects_empty_optional_string():
    with pytest.raises(ValidationError):
        PersonalizationRequest(
            company_name="Acme",
            product_or_service_offered="Freight API",
            notes="",
        )


def test_request_rejects_invalid_website_url():
    with pytest.raises(ValidationError):
        PersonalizationRequest(
            company_name="Acme",
            product_or_service_offered="Freight API",
            website_url="not-a-url",
        )


def test_request_rejects_empty_string_in_list():
    with pytest.raises(ValidationError):
        PersonalizationRequest(
            company_name="Acme",
            product_or_service_offered="Freight API",
            known_pain_points=["Valid", "  "],
        )


def test_request_trims_list_items():
    request = PersonalizationRequest(
        company_name="Acme",
        product_or_service_offered="Freight API",
        known_triggers=["  New funding round  "],
    )
    assert request.known_triggers == ["New funding round"]


# -- PersonalizationResponse ------------------------------------------------

def _valid_response_kwargs() -> dict:
    return {
        "company_name": "Acme GmbH",
        "personalization_summary": "Focus on operational efficiency gains.",
        "confidence_score": 0.5,
    }


def test_response_accepts_valid_payload():
    response = PersonalizationResponse(**_valid_response_kwargs())

    assert response.company_name == "Acme GmbH"
    assert response.confidence_score == 0.5
    assert response.relevant_observations == []
    assert response.possible_conversation_starters == []
    assert response.suggested_ctas == []
    assert response.do_not_use_claims == []
    assert response.missing_information == []
    assert response.sources_used == []


def test_response_clamps_confidence_above_one():
    response = PersonalizationResponse(
        **{**_valid_response_kwargs(), "confidence_score": 4.2}
    )
    assert response.confidence_score == 1.0


def test_response_clamps_confidence_below_zero():
    response = PersonalizationResponse(
        **{**_valid_response_kwargs(), "confidence_score": -1.0}
    )
    assert response.confidence_score == 0.0


def test_response_rejects_non_numeric_confidence():
    with pytest.raises(ValidationError):
        PersonalizationResponse(
            **{**_valid_response_kwargs(), "confidence_score": "high"}
        )


def test_response_requires_personalization_summary():
    with pytest.raises(ValidationError):
        PersonalizationResponse(company_name="Acme", confidence_score=0.5)
