import pytest
from pydantic import ValidationError

from backend.agents.company_intelligence.schemas import (
    CompanyIntelligenceRequest,
    CompanyIntelligenceResponse,
)


# -- CompanyIntelligenceRequest -------------------------------------------

def test_request_accepts_minimal_valid_input():
    request = CompanyIntelligenceRequest(company_name="Acme GmbH")

    assert request.company_name == "Acme GmbH"
    assert request.website_url is None
    assert request.known_products is None
    assert request.known_customers is None


def test_request_accepts_full_valid_input():
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

    assert str(request.website_url) == "https://acme.example.com/"
    assert request.known_products == ["Freight API", "Tracking"]
    assert request.known_customers == ["Beta AG"]


def test_request_requires_company_name():
    with pytest.raises(ValidationError):
        CompanyIntelligenceRequest()


def test_request_rejects_empty_company_name():
    with pytest.raises(ValidationError):
        CompanyIntelligenceRequest(company_name="")


def test_request_rejects_whitespace_only_company_name():
    with pytest.raises(ValidationError):
        CompanyIntelligenceRequest(company_name="   ")


def test_request_trims_string_fields():
    request = CompanyIntelligenceRequest(
        company_name="  Acme GmbH  ", industry="  SaaS "
    )
    assert request.company_name == "Acme GmbH"
    assert request.industry == "SaaS"


def test_request_rejects_empty_optional_string():
    with pytest.raises(ValidationError):
        CompanyIntelligenceRequest(company_name="Acme", company_description="")


def test_request_rejects_invalid_website_url():
    with pytest.raises(ValidationError):
        CompanyIntelligenceRequest(company_name="Acme", website_url="not-a-url")


def test_request_rejects_empty_string_in_list():
    with pytest.raises(ValidationError):
        CompanyIntelligenceRequest(
            company_name="Acme", known_products=["Valid", "  "]
        )


def test_request_trims_list_items():
    request = CompanyIntelligenceRequest(
        company_name="Acme", known_customers=["  Beta AG  "]
    )
    assert request.known_customers == ["Beta AG"]


# -- CompanyIntelligenceResponse ------------------------------------------

def _valid_response_kwargs() -> dict:
    return {
        "company_name": "Acme GmbH",
        "business_summary": "A logistics company.",
        "positioning_summary": "Positioned as an efficiency-focused carrier.",
        "confidence_score": 0.5,
    }


def test_response_accepts_valid_payload():
    response = CompanyIntelligenceResponse(**_valid_response_kwargs())

    assert response.company_name == "Acme GmbH"
    assert response.confidence_score == 0.5
    assert response.products_and_services == []
    assert response.possible_competitive_context == []
    assert response.personalization_hooks == []
    assert response.missing_information == []
    assert response.sources_used == []


def test_response_clamps_confidence_above_one():
    response = CompanyIntelligenceResponse(
        **{**_valid_response_kwargs(), "confidence_score": 4.2}
    )
    assert response.confidence_score == 1.0


def test_response_clamps_confidence_below_zero():
    response = CompanyIntelligenceResponse(
        **{**_valid_response_kwargs(), "confidence_score": -1.0}
    )
    assert response.confidence_score == 0.0


def test_response_rejects_non_numeric_confidence():
    with pytest.raises(ValidationError):
        CompanyIntelligenceResponse(
            **{**_valid_response_kwargs(), "confidence_score": "high"}
        )


def test_response_requires_business_summary():
    with pytest.raises(ValidationError):
        CompanyIntelligenceResponse(
            company_name="Acme",
            positioning_summary="x",
            confidence_score=0.5,
        )
