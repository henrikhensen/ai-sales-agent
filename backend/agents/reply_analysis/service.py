"""Reply Analysis Agent and its orchestrating service.

``ReplyAnalysisAgent`` plugs into the Phase 3 agent framework
(:class:`BaseAgent`) and turns a :class:`ReplyAnalysisRequest` into a
validated :class:`ReplyAnalysisResponse` via the configured LLM provider.

``ReplyAnalysisService`` is the application-layer entry point used by the
API. It owns the business rules that must not live in the router: running the
agent, translating framework validation failures into a domain-specific error,
and grounding the identity field in the user's input. This agent never sends a
reply, books a meeting, or contacts anyone — it produces analysis and
recommendations only, for mandatory human review.
"""

from __future__ import annotations

from backend.agents.base import BaseAgent
from backend.agents.exceptions import AgentOutputValidationError
from backend.agents.reply_analysis.exceptions import InvalidReplyAnalysisOutputError
from backend.agents.reply_analysis.prompt import (
    REPLY_ANALYSIS_SYSTEM_PROMPT,
    build_reply_analysis_prompt,
)
from backend.agents.reply_analysis.schemas import (
    ReplyAnalysisRequest,
    ReplyAnalysisResponse,
)
from backend.infrastructure.llm.base import LLMProvider


class ReplyAnalysisAgent(BaseAgent[ReplyAnalysisRequest, ReplyAnalysisResponse]):
    """Classifies and analyses a lead's reply from user-supplied context.

    Never sends a reply, books a meeting, or contacts anyone, and fetches no
    external data; all compliance rules are enforced through the system
    prompt and the output schema.
    """

    name = "reply_analysis"
    input_model = ReplyAnalysisRequest
    output_model = ReplyAnalysisResponse
    system_prompt = REPLY_ANALYSIS_SYSTEM_PROMPT

    def build_prompt(self, agent_input: ReplyAnalysisRequest) -> str:
        return build_reply_analysis_prompt(agent_input)


class ReplyAnalysisService:
    """Application service that runs the Reply Analysis Agent."""

    def __init__(self, llm: LLMProvider) -> None:
        self._agent = ReplyAnalysisAgent(llm)

    async def analyze(self, request: ReplyAnalysisRequest) -> ReplyAnalysisResponse:
        """Run the agent and return a grounded, validated reply analysis.

        Raises:
            InvalidReplyAnalysisOutputError: if the provider returns output
                that does not conform to :class:`ReplyAnalysisResponse`.
        """
        try:
            result = await self._agent.run(request)
        except AgentOutputValidationError as exc:
            raise InvalidReplyAnalysisOutputError(exc.reason) from exc

        # Identity fact comes from the user, never from the model.
        return result.output.model_copy(
            update={"company_name": request.company_name}
        )
