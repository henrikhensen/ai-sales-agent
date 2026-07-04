"""Email Draft Agent and its orchestrating service.

``EmailDraftAgent`` plugs into the Phase 3 agent framework (:class:`BaseAgent`)
and turns an :class:`EmailDraftRequest` into a validated
:class:`EmailDraftResponse` via the configured LLM provider.

``EmailDraftService`` is the application-layer entry point used by the API. It
owns the business rules that must not live in the router: running the agent,
translating framework validation failures into a domain-specific error, and
grounding the identity fields in the user's input. This agent never sends an
email — it produces a draft only, for mandatory human review.
"""

from __future__ import annotations

from backend.agents.base import BaseAgent
from backend.agents.email_draft.exceptions import InvalidEmailDraftOutputError
from backend.agents.email_draft.prompt import (
    EMAIL_DRAFT_SYSTEM_PROMPT,
    build_email_draft_prompt,
)
from backend.agents.email_draft.schemas import EmailDraftRequest, EmailDraftResponse
from backend.agents.exceptions import AgentOutputValidationError
from backend.infrastructure.llm.base import LLMProvider


class EmailDraftAgent(BaseAgent[EmailDraftRequest, EmailDraftResponse]):
    """Produces a human-reviewable email draft from user-supplied context.

    Never sends anything and fetches no external data; all compliance rules
    are enforced through the system prompt and the output schema.
    """

    name = "email_draft"
    input_model = EmailDraftRequest
    output_model = EmailDraftResponse
    system_prompt = EMAIL_DRAFT_SYSTEM_PROMPT

    def build_prompt(self, agent_input: EmailDraftRequest) -> str:
        return build_email_draft_prompt(agent_input)


class EmailDraftService:
    """Application service that runs the Email Draft Agent."""

    def __init__(self, llm: LLMProvider) -> None:
        self._agent = EmailDraftAgent(llm)

    async def draft(self, request: EmailDraftRequest) -> EmailDraftResponse:
        """Run the agent and return a grounded, validated email draft.

        Raises:
            InvalidEmailDraftOutputError: if the provider returns output that
                does not conform to :class:`EmailDraftResponse`.
        """
        try:
            result = await self._agent.run(request)
        except AgentOutputValidationError as exc:
            raise InvalidEmailDraftOutputError(exc.reason) from exc

        # Identity facts come from the user, never from the model.
        return result.output.model_copy(
            update={"company_name": request.company_name}
        )
