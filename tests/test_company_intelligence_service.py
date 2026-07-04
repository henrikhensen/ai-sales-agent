from typing import Any

import pytest

from backend.agents.company_intelligence.exceptions import (
    InvalidCompanyIntelligenceOutputError,
)
from backend.agents.company_intelligence.schemas import (
    CompanyIntelligenceRequest,
    CompanyIntelligenceResponse,
)
from backend.agents.company_intelligence.service import CompanyIntelligenceService
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


async def test_service_returns_validated_profile_with_mock_provider():
    service = CompanyIntelligenceService(MockLLMProvider())
    request = CompanyIntelligenceRequest(
        company_name="Acme GmbH",
        website_url="https://acme.example.com",
        industry="Logistics",
        location="Berlin",
        known_products=["Freight API"],
    )

    response = await service.analyze(request)

    assert isinstance(response, CompanyIntelligenceResponse)
    # Identity fields are grounded in the input, never fabricated.
    assert response.company_name == "Acme GmbH"
    assert response.website_url == "https://acme.example.com/"
    assert response.industry == "Logistics"
    assert response.location == "Berlin"
    # Confidence stays within the valid range even from the mock provider.
    assert 0.0 <= response.confidence_score <= 1.0


async def test_service_grounds_optional_identity_fields_as_none():
    service = CompanyIntelligenceService(MockLLMProvider())
    request = CompanyIntelligenceRequest(company_name="Acme GmbH")

    response = await service.analyze(request)

    assert response.company_name == "Acme GmbH"
    assert response.website_url is None
    assert response.industry is None
    assert response.location is None


async def test_service_raises_domain_error_on_invalid_output():
    service = CompanyIntelligenceService(BrokenLLMProvider())
    request = CompanyIntelligenceRequest(company_name="Acme GmbH")

    with pytest.raises(InvalidCompanyIntelligenceOutputError):
        await service.analyze(request)
