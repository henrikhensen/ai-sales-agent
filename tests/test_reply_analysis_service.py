from typing import Any

import pytest

from backend.agents.reply_analysis.exceptions import InvalidReplyAnalysisOutputError
from backend.agents.reply_analysis.schemas import (
    ReplyAnalysisRequest,
    ReplyAnalysisResponse,
)
from backend.agents.reply_analysis.service import ReplyAnalysisService
from backend.infrastructure.llm.base import LLMProvider
from backend.infrastructure.llm.mock_provider import MockLLMProvider


class BrokenLLMProvider(LLMProvider):
    """Returns output that cannot satisfy the response schema."""

    name = "broken"

    async def generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        return {"confidence_score": "definitely not a number"}


async def test_service_returns_validated_analysis_with_mock_provider():
    service = ReplyAnalysisService(MockLLMProvider())
    request = ReplyAnalysisRequest(
        company_name="Acme GmbH",
        reply_text="Thanks, could we schedule a call next week?",
    )

    response = await service.analyze(request)

    assert isinstance(response, ReplyAnalysisResponse)
    # Identity field is grounded in the input, never fabricated.
    assert response.company_name == "Acme GmbH"
    # Enum fields must stay within their allowed value sets.
    assert response.classification in (
        "interested",
        "meeting_request",
        "question",
        "objection",
        "not_interested",
        "out_of_office",
        "unclear",
    )
    assert response.sentiment in ("positive", "neutral", "negative", "unclear")
    assert response.urgency in ("low", "medium", "high", "unclear")
    # Confidence stays within the valid range even from the mock provider.
    assert 0.0 <= response.confidence_score <= 1.0


async def test_service_grounds_company_name_regardless_of_provider_output():
    service = ReplyAnalysisService(MockLLMProvider())
    request = ReplyAnalysisRequest(
        company_name="Acme GmbH", reply_text="Not interested."
    )

    response = await service.analyze(request)

    assert response.company_name == "Acme GmbH"


async def test_service_raises_domain_error_on_invalid_output():
    service = ReplyAnalysisService(BrokenLLMProvider())
    request = ReplyAnalysisRequest(
        company_name="Acme GmbH", reply_text="Not interested."
    )

    with pytest.raises(InvalidReplyAnalysisOutputError):
        await service.analyze(request)
