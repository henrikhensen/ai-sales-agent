from typing import Any

import pytest

from backend.agents.email_draft.exceptions import InvalidEmailDraftOutputError
from backend.agents.email_draft.schemas import EmailDraftRequest, EmailDraftResponse
from backend.agents.email_draft.service import EmailDraftService
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


async def test_service_returns_validated_draft_with_mock_provider():
    service = EmailDraftService(MockLLMProvider())
    request = EmailDraftRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight visibility platform",
        recipient_name="Jane Doe",
    )

    response = await service.draft(request)

    assert isinstance(response, EmailDraftResponse)
    # Identity field is grounded in the input, never fabricated.
    assert response.company_name == "Acme GmbH"
    # Confidence stays within the valid range even from the mock provider.
    assert 0.0 <= response.confidence_score <= 1.0


async def test_service_grounds_company_name_regardless_of_provider_output():
    service = EmailDraftService(MockLLMProvider())
    request = EmailDraftRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    response = await service.draft(request)

    assert response.company_name == "Acme GmbH"


async def test_service_raises_domain_error_on_invalid_output():
    service = EmailDraftService(BrokenLLMProvider())
    request = EmailDraftRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    with pytest.raises(InvalidEmailDraftOutputError):
        await service.draft(request)
