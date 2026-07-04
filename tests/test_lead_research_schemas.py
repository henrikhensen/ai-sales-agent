import pytest
from pydantic import ValidationError

from backend.agents.lead_research.schemas import (
    LeadResearchRequest,
    LeadResearchResponse,
)


# -- LeadResearchRequest --------------------------------------------------

def test_request_accepts_minimal_valid_input():
    request = LeadResearchRequest(company_name="Acme GmbH")

    assert request.company_name == "Acme GmbH"
    assert request.website_url is None
    assert request.industry is None
    assert request.location is None
    assert request.notes is None


def test_request_accepts_full_valid_input():
    request = LeadResearchRequest(
        company_name="Acme GmbH",
        website_url="https://acme.example.com",
        industry="Logistics",
        location="Berlin",
        notes="Met at trade fair.",
    )

    assert str(request.website_url) == "https://acme.example.com/"
    assert request.industry == "Logistics"


def test_request_requires_company_name():
    with pytest.raises(ValidationError):
        LeadResearchRequest()


def test_request_rejects_empty_company_name():
    with pytest.raises(ValidationError):
        LeadResearchRequest(company_name="")


def test_request_rejects_whitespace_only_company_name():
    with pytest.raises(ValidationError):
        LeadResearchRequest(company_name="   ")


def test_request_trims_string_fields():
    request = LeadResearchRequest(company_name="  Acme GmbH  ", industry="  SaaS ")

    assert request.company_name == "Acme GmbH"
    assert request.industry == "SaaS"


def test_request_rejects_empty_optional_string():
    with pytest.raises(ValidationError):
        LeadResearchRequest(company_name="Acme", industry="")


def test_request_rejects_invalid_website_url():
    with pytest.raises(ValidationError):
        LeadResearchRequest(company_name="Acme", website_url="not-a-url")


# -- LeadResearchResponse -------------------------------------------------

def _valid_response_kwargs() -> dict:
    return {
        "company_name": "Acme GmbH",
        "short_summary": "A logistics company.",
        "confidence_score": 0.5,
    }


def test_response_accepts_valid_payload():
    response = LeadResearchResponse(**_valid_response_kwargs())

    assert response.company_name == "Acme GmbH"
    assert response.confidence_score == 0.5
    assert response.target_customers == []
    assert response.missing_information == []
    assert response.sources_used == []


def test_response_clamps_confidence_above_one():
    response = LeadResearchResponse(
        **{**_valid_response_kwargs(), "confidence_score": 5.0}
    )
    assert response.confidence_score == 1.0


def test_response_clamps_confidence_below_zero():
    response = LeadResearchResponse(
        **{**_valid_response_kwargs(), "confidence_score": -3.0}
    )
    assert response.confidence_score == 0.0


def test_response_rejects_non_numeric_confidence():
    with pytest.raises(ValidationError):
        LeadResearchResponse(
            **{**_valid_response_kwargs(), "confidence_score": "high"}
        )


def test_response_requires_short_summary():
    with pytest.raises(ValidationError):
        LeadResearchResponse(company_name="Acme", confidence_score=0.5)
