"""Lead Research Agent and its orchestrating service.

``LeadResearchAgent`` plugs into the Phase 3 agent framework (:class:`BaseAgent`)
and turns a :class:`LeadResearchRequest` into a validated
:class:`LeadResearchResponse` via the configured LLM provider.

``LeadResearchService`` is the application-layer entry point used by the API.
It owns the business rules that must not live in the router: running the agent,
translating framework validation failures into a domain-specific error, and
grounding the identity fields (company name, website, industry, location) in
the user's input so the model can never fabricate them.
"""

from __future__ import annotations

from backend.agents.base import BaseAgent
from backend.agents.exceptions import AgentOutputValidationError
from backend.agents.lead_research.exceptions import InvalidLeadResearchOutputError
from backend.agents.lead_research.prompt import (
    LEAD_RESEARCH_SYSTEM_PROMPT,
    build_lead_research_prompt,
)
from backend.agents.lead_research.schemas import (
    LeadResearchRequest,
    LeadResearchResponse,
)
from backend.infrastructure.llm.base import LLMProvider


class LeadResearchAgent(BaseAgent[LeadResearchRequest, LeadResearchResponse]):
    """Analyses a company from user-supplied information only.

    Produces a structured lead profile. It performs no outreach and fetches no
    external data; all compliance rules are enforced through the system prompt
    and the output schema.
    """

    name = "lead_research"
    input_model = LeadResearchRequest
    output_model = LeadResearchResponse
    system_prompt = LEAD_RESEARCH_SYSTEM_PROMPT

    def build_prompt(self, agent_input: LeadResearchRequest) -> str:
        return build_lead_research_prompt(agent_input)


class LeadResearchService:
    """Application service that runs the Lead Research Agent."""

    def __init__(self, llm: LLMProvider) -> None:
        self._agent = LeadResearchAgent(llm)

    async def research(self, request: LeadResearchRequest) -> LeadResearchResponse:
        """Run the agent and return a grounded, validated lead profile.

        Raises:
            InvalidLeadResearchOutputError: if the provider returns output that
                does not conform to :class:`LeadResearchResponse`.
        """
        try:
            result = await self._agent.run(request)
        except AgentOutputValidationError as exc:
            raise InvalidLeadResearchOutputError(exc.reason) from exc

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
