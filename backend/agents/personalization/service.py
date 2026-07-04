"""Personalization Engine and its orchestrating service.

``PersonalizationAgent`` plugs into the Phase 3 agent framework
(:class:`BaseAgent`) and turns a :class:`PersonalizationRequest` into a
validated :class:`PersonalizationResponse` via the configured LLM provider.

``PersonalizationService`` is the application-layer entry point used by the
API. It owns the business rules that must not live in the router: running the
agent, translating framework validation failures into a domain-specific error,
and grounding the identity fields in the user's input.
"""

from __future__ import annotations

from backend.agents.base import BaseAgent
from backend.agents.exceptions import AgentOutputValidationError
from backend.agents.personalization.exceptions import (
    InvalidPersonalizationOutputError,
)
from backend.agents.personalization.prompt import (
    PERSONALIZATION_SYSTEM_PROMPT,
    build_personalization_prompt,
)
from backend.agents.personalization.schemas import (
    PersonalizationRequest,
    PersonalizationResponse,
)
from backend.infrastructure.llm.base import LLMProvider


class PersonalizationAgent(BaseAgent[PersonalizationRequest, PersonalizationResponse]):
    """Produces a structured personalization strategy from user-supplied context.

    Performs no outreach and fetches no external data; all compliance rules are
    enforced through the system prompt and the output schema.
    """

    name = "personalization"
    input_model = PersonalizationRequest
    output_model = PersonalizationResponse
    system_prompt = PERSONALIZATION_SYSTEM_PROMPT

    def build_prompt(self, agent_input: PersonalizationRequest) -> str:
        return build_personalization_prompt(agent_input)


class PersonalizationService:
    """Application service that runs the Personalization Engine."""

    def __init__(self, llm: LLMProvider) -> None:
        self._agent = PersonalizationAgent(llm)

    async def personalize(
        self, request: PersonalizationRequest
    ) -> PersonalizationResponse:
        """Run the agent and return a grounded, validated personalization strategy.

        Raises:
            InvalidPersonalizationOutputError: if the provider returns output
                that does not conform to :class:`PersonalizationResponse`.
        """
        try:
            result = await self._agent.run(request)
        except AgentOutputValidationError as exc:
            raise InvalidPersonalizationOutputError(exc.reason) from exc

        # Identity facts come from the user, never from the model.
        return result.output.model_copy(
            update={
                "company_name": request.company_name,
                "website_url": (
                    str(request.website_url) if request.website_url else None
                ),
                "industry": request.industry,
            }
        )
