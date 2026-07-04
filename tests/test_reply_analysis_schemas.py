import pytest
from pydantic import ValidationError

from backend.agents.reply_analysis.schemas import (
    ReplyAnalysisRequest,
    ReplyAnalysisResponse,
)


# -- ReplyAnalysisRequest ----------------------------------------------------

def test_request_accepts_minimal_valid_input():
    request = ReplyAnalysisRequest(
        company_name="Acme GmbH", reply_text="Thanks, but we're not interested."
    )

    assert request.company_name == "Acme GmbH"
    assert request.reply_text == "Thanks, but we're not interested."
    assert request.lead_name is None
    assert request.original_email_subject is None


def test_request_accepts_full_valid_input():
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

    assert request.lead_name == "Jane Doe"
    assert request.reply_text == "Können wir nächste Woche telefonieren?"


def test_request_requires_company_name():
    with pytest.raises(ValidationError):
        ReplyAnalysisRequest(reply_text="Not interested.")


def test_request_requires_reply_text():
    with pytest.raises(ValidationError):
        ReplyAnalysisRequest(company_name="Acme GmbH")


def test_request_rejects_empty_company_name():
    with pytest.raises(ValidationError):
        ReplyAnalysisRequest(company_name="", reply_text="Not interested.")


def test_request_rejects_whitespace_only_reply_text():
    with pytest.raises(ValidationError):
        ReplyAnalysisRequest(company_name="Acme GmbH", reply_text="   ")


def test_request_trims_string_fields():
    request = ReplyAnalysisRequest(
        company_name="  Acme GmbH  ", reply_text="  Sounds good.  "
    )
    assert request.company_name == "Acme GmbH"
    assert request.reply_text == "Sounds good."


def test_request_rejects_empty_optional_string():
    with pytest.raises(ValidationError):
        ReplyAnalysisRequest(
            company_name="Acme", reply_text="Sounds good.", notes=""
        )


# -- ReplyAnalysisResponse ----------------------------------------------------

def _valid_response_kwargs() -> dict:
    return {
        "company_name": "Acme GmbH",
        "classification": "interested",
        "sentiment": "positive",
        "urgency": "medium",
        "summary": "Lead wants to schedule a call.",
        "recommended_next_action": "Propose two time slots for a human to confirm.",
        "confidence_score": 0.7,
    }


def test_response_accepts_valid_payload():
    response = ReplyAnalysisResponse(**_valid_response_kwargs())

    assert response.company_name == "Acme GmbH"
    assert response.classification == "interested"
    assert response.sentiment == "positive"
    assert response.urgency == "medium"
    assert response.confidence_score == 0.7
    assert response.detected_intent == []
    assert response.questions_to_answer == []
    assert response.do_not_continue_if == []
    assert response.suggested_reply is None


def test_response_rejects_invalid_classification():
    with pytest.raises(ValidationError):
        ReplyAnalysisResponse(
            **{**_valid_response_kwargs(), "classification": "very_interested"}
        )


def test_response_rejects_invalid_sentiment():
    with pytest.raises(ValidationError):
        ReplyAnalysisResponse(**{**_valid_response_kwargs(), "sentiment": "happy"})


def test_response_rejects_invalid_urgency():
    with pytest.raises(ValidationError):
        ReplyAnalysisResponse(**{**_valid_response_kwargs(), "urgency": "asap"})


def test_response_clamps_confidence_above_one():
    response = ReplyAnalysisResponse(
        **{**_valid_response_kwargs(), "confidence_score": 4.2}
    )
    assert response.confidence_score == 1.0


def test_response_clamps_confidence_below_zero():
    response = ReplyAnalysisResponse(
        **{**_valid_response_kwargs(), "confidence_score": -1.0}
    )
    assert response.confidence_score == 0.0


def test_response_rejects_non_numeric_confidence():
    with pytest.raises(ValidationError):
        ReplyAnalysisResponse(
            **{**_valid_response_kwargs(), "confidence_score": "high"}
        )


def test_response_requires_summary_and_recommended_next_action():
    with pytest.raises(ValidationError):
        ReplyAnalysisResponse(
            company_name="Acme",
            classification="unclear",
            sentiment="unclear",
            urgency="unclear",
            confidence_score=0.2,
        )
