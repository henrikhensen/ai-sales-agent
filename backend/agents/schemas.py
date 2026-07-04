from typing import Any, Generic, TypeVar

from pydantic import BaseModel


class AgentInput(BaseModel):
    """Base class for all agent inputs."""


class AgentOutput(BaseModel):
    """Base class for all agent outputs (the LLM-produced, validated result)."""


OutputT = TypeVar("OutputT", bound=AgentOutput)


class AgentRunResult(BaseModel, Generic[OutputT]):
    """The full result of running an agent once."""

    agent: str
    provider: str
    output: OutputT
    raw: dict[str, Any]
