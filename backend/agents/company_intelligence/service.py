"""Company Intelligence Agent and its orchestrating service.

``CompanyIntelligenceAgent`` plugs into the Phase 3 agent framework
(:class:`BaseAgent`) and turns a :class:`CompanyIntelligenceRequest` into a
validated :class:`CompanyIntelligenceResponse` via the configured LLM provider.

``CompanyIntelligenceService`` is the application-layer entry point used by the
API. It owns the business rules that must not live in the router: running the
agent, translating framework validation failures into a domain-specific error,
and grounding the identity fields in the user's input.
"""

from __future__ import annotations

from backend.agents.base import BaseAgent
from backend.agents.company_intelligence.exceptions import (
    InvalidCompanyIntelligenceOutputError,
)
from backend.agents.company_intelligence.prompt import (
    COMPANY_INTELLIGENCE_SYSTEM_PROMPT,
    build_company_intelligence_prompt,
)
from backend.agents.company_intelligence.schemas import (
    CompanyIntelligenceRequest,
    CompanyIntelligenceResponse,
)
from backend.agents.exceptions import AgentOutputValidationError
from backend.infrastructure.llm.base import LLMProvider


class CompanyIntelligenceAgent(
    BaseAgent[CompanyIntelligenceRequest, CompanyIntelligenceResponse]
):
    """Produces a deeper, strategic company profile from user-supplied input only.

    Performs no outreach and fetches no external data; all compliance rules are
    enforced through the system prompt and the output schema.
    """

    name = "company_intelligence"
    input_model = CompanyIntelligenceRequest
    output_model = CompanyIntelligenceResponse
    system_prompt = COMPANY_INTELLIGENCE_SYSTEM_PROMPT

    def build_prompt(self, agent_input: CompanyIntelligenceRequest) -> str:
        return build_company_intelligence_prompt(agent_input)


class CompanyIntelligenceService:
    """Application service that runs the Company Intelligence Agent."""

    def __init__(self, llm: LLMProvider) -> None:
        self._agent = CompanyIntelligenceAgent(llm)

    async def analyze(
        self, request: CompanyIntelligenceRequest
    ) -> CompanyIntelligenceResponse:
        """Run the agent and return a grounded, validated company profile.

        Raises:
            InvalidCompanyIntelligenceOutputError: if the provider returns
                output that does not conform to
                :class:`CompanyIntelligenceResponse`.
        """
        try:
            result = await self._agent.run(request)
        except AgentOutputValidationError as exc:
            raise InvalidCompanyIntelligenceOutputError(exc.reason) from exc

        # Identity facts come from the user, never from the model.
        return result.output.model_copy(
            update={
                "company_name": request.company_name,
                "website_url": (
                    str(request.website_url) if request.website_url else None
                ),
                "industry": request.industry,
                "location": request.location,
            }
        )
