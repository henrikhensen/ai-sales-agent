from typing import Any

import pytest

from backend.agents.lead_research.exceptions import InvalidLeadResearchOutputError
from backend.agents.lead_research.schemas import (
    LeadResearchRequest,
    LeadResearchResponse,
)
from backend.agents.lead_research.service import LeadResearchService
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
    service = LeadResearchService(MockLLMProvider())
    request = LeadResearchRequest(
        company_name="Acme GmbH",
        website_url="https://acme.example.com",
        industry="Logistics",
        location="Berlin",
    )

    response = await service.research(request)

    assert isinstance(response, LeadResearchResponse)
    # Identity fields are grounded in the input, never fabricated.
    assert response.company_name == "Acme GmbH"
    assert response.website_url == "https://acme.example.com/"
    assert response.industry == "Logistics"
    assert response.location == "Berlin"
    # Confidence stays within the valid range even from the mock provider.
    assert 0.0 <= response.confidence_score <= 1.0


async def test_service_grounds_optional_identity_fields_as_none():
    service = LeadResearchService(MockLLMProvider())
    request = LeadResearchRequest(company_name="Acme GmbH")

    response = await service.research(request)

    assert response.company_name == "Acme GmbH"
    assert response.website_url is None
    assert response.industry is None
    assert response.location is None


async def test_service_raises_domain_error_on_invalid_output():
    service = LeadResearchService(BrokenLLMProvider())
    request = LeadResearchRequest(company_name="Acme GmbH")

    with pytest.raises(InvalidLeadResearchOutputError):
        await service.research(request)
