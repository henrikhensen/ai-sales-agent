from typing import Any

import pytest

from backend.agents.personalization.exceptions import (
    InvalidPersonalizationOutputError,
)
from backend.agents.personalization.schemas import (
    PersonalizationRequest,
    PersonalizationResponse,
)
from backend.agents.personalization.service import PersonalizationService
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


async def test_service_returns_validated_strategy_with_mock_provider():
    service = PersonalizationService(MockLLMProvider())
    request = PersonalizationRequest(
        company_name="Acme GmbH",
        website_url="https://acme.example.com",
        industry="Logistics",
        product_or_service_offered="Freight visibility platform",
    )

    response = await service.personalize(request)

    assert isinstance(response, PersonalizationResponse)
    # Identity fields are grounded in the input, never fabricated.
    assert response.company_name == "Acme GmbH"
    assert response.website_url == "https://acme.example.com/"
    assert response.industry == "Logistics"
    # Confidence stays within the valid range even from the mock provider.
    assert 0.0 <= response.confidence_score <= 1.0


async def test_service_grounds_optional_identity_fields_as_none():
    service = PersonalizationService(MockLLMProvider())
    request = PersonalizationRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    response = await service.personalize(request)

    assert response.company_name == "Acme GmbH"
    assert response.website_url is None
    assert response.industry is None


async def test_service_raises_domain_error_on_invalid_output():
    service = PersonalizationService(BrokenLLMProvider())
    request = PersonalizationRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    with pytest.raises(InvalidPersonalizationOutputError):
        await service.personalize(request)
