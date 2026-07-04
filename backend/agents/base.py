from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import ValidationError

from backend.agents.exceptions import AgentOutputValidationError
from backend.agents.schemas import AgentInput, AgentOutput, AgentRunResult
from backend.infrastructure.llm.base import LLMProvider

InputT = TypeVar("InputT", bound=AgentInput)
OutputT = TypeVar("OutputT", bound=AgentOutput)


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Base class for all agents.

    An agent turns a typed :class:`AgentInput` into a typed :class:`AgentOutput`
    by (1) building a prompt, (2) asking the configured LLM provider for JSON
    conforming to the output schema, and (3) validating that JSON. Subclasses
    declare ``name``, ``input_model``, ``output_model``, ``system_prompt`` and
    implement :meth:`build_prompt`.
    """

    #: Unique registry name for the agent.
    name: str
    #: Pydantic model describing accepted input.
    input_model: type[InputT]
    #: Pydantic model describing produced output.
    output_model: type[OutputT]
    #: System prompt sent to the LLM.
    system_prompt: str

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    @abstractmethod
    def build_prompt(self, agent_input: InputT) -> str:
        """Render the user prompt for a given input."""

    async def run(self, agent_input: InputT) -> AgentRunResult[OutputT]:
        """Execute the agent once and return a validated result."""
        prompt = self.build_prompt(agent_input)
        schema = self.output_model.model_json_schema()

        raw = await self._llm.generate_json(
            system=self.system_prompt,
            prompt=prompt,
            schema=schema,
        )

        try:
            output = self.output_model.model_validate(raw)
        except ValidationError as exc:
            raise AgentOutputValidationError(self.name, str(exc)) from exc

        return AgentRunResult(
            agent=self.name,
            provider=self._llm.name,
            output=output,
            raw=raw,
        )
