import pytest
from pydantic import ValidationError

from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)


# -- SalesWorkflowRequest ----------------------------------------------------

def test_request_accepts_minimal_valid_input():
    request = SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    assert request.company_name == "Acme GmbH"
    assert request.product_or_service_offered == "Freight API"
    assert request.tone == "professional"
    assert request.language == "German"
    assert request.website_url is None


def test_request_accepts_full_valid_input():
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        website_url="https://acme.example.com",
        industry="Logistics",
        location="Berlin",
        company_description="A logistics provider.",
        website_text="We move freight across Europe.",
        target_persona="Head of Operations",
        product_or_service_offered="Freight visibility platform",
        sender_name="John Smith",
        sender_company="Beta Vertrieb GmbH",
        tone="consultative",
        language="English",
        notes="Met at trade fair.",
    )

    assert str(request.website_url) == "https://acme.example.com/"
    assert request.tone == "consultative"
    assert request.language == "English"


def test_request_requires_company_name():
    with pytest.raises(ValidationError):
        SalesWorkflowRequest(product_or_service_offered="Freight API")


def test_request_requires_product_or_service_offered():
    with pytest.raises(ValidationError):
        SalesWorkflowRequest(company_name="Acme GmbH")


def test_request_rejects_empty_company_name():
    with pytest.raises(ValidationError):
        SalesWorkflowRequest(
            company_name="", product_or_service_offered="Freight API"
        )


def test_request_rejects_whitespace_only_product_or_service_offered():
    with pytest.raises(ValidationError):
        SalesWorkflowRequest(company_name="Acme GmbH", product_or_service_offered="   ")


def test_request_trims_string_fields():
    request = SalesWorkflowRequest(
        company_name="  Acme GmbH  ",
        product_or_service_offered="  Freight API  ",
    )
    assert request.company_name == "Acme GmbH"
    assert request.product_or_service_offered == "Freight API"


def test_request_rejects_invalid_website_url():
    with pytest.raises(ValidationError):
        SalesWorkflowRequest(
            company_name="Acme GmbH",
            product_or_service_offered="Freight API",
            website_url="not-a-url",
        )


def test_request_rejects_invalid_tone():
    with pytest.raises(ValidationError):
        SalesWorkflowRequest(
            company_name="Acme GmbH",
            product_or_service_offered="Freight API",
            tone="aggressive",
        )


# -- SalesWorkflowResponse ----------------------------------------------------

def _minimal_agent_kwargs() -> dict:
    return {
        "lead_research": {
            "company_name": "Acme GmbH",
            "short_summary": "A logistics company.",
            "confidence_score": 0.5,
        },
        "company_intelligence": {
            "company_name": "Acme GmbH",
            "business_summary": "A logistics company.",
            "positioning_summary": "Efficiency-focused carrier.",
            "confidence_score": 0.5,
        },
        "personalization": {
            "company_name": "Acme GmbH",
            "personalization_summary": "Focus on efficiency gains.",
            "confidence_score": 0.5,
        },
        "email_draft": {
            "company_name": "Acme GmbH",
            "email_body": "Dear team, ...",
            "confidence_score": 0.5,
        },
    }


def test_response_accepts_valid_payload():
    response = SalesWorkflowResponse(
        workflow_id="wf-1",
        status="completed",
        company_name="Acme GmbH",
        human_review_required=True,
        confidence_score=0.5,
        **_minimal_agent_kwargs(),
    )

    assert response.workflow_id == "wf-1"
    assert response.status == "completed"
    assert response.human_review_required is True
    assert response.review_checklist == []
    assert response.compliance_notes == []
    assert response.missing_information == []


def test_response_requires_all_step_outputs():
    with pytest.raises(ValidationError):
        SalesWorkflowResponse(
            workflow_id="wf-1",
            status="completed",
            company_name="Acme GmbH",
            confidence_score=0.5,
        )


def test_response_rejects_confidence_out_of_range():
    with pytest.raises(ValidationError):
        SalesWorkflowResponse(
            workflow_id="wf-1",
            status="completed",
            company_name="Acme GmbH",
            confidence_score=1.5,
            **_minimal_agent_kwargs(),
        )
