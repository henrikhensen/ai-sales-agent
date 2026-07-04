from __future__ import annotations

from typing import TYPE_CHECKING

from backend.agents.exceptions import (
    AgentAlreadyRegisteredError,
    AgentNotFoundError,
)

if TYPE_CHECKING:
    from backend.agents.base import BaseAgent
    from backend.infrastructure.llm.base import LLMProvider


class AgentRegistry:
    """Registry mapping agent names to agent classes.

    Agents are registered by class and instantiated on demand with a concrete
    LLM provider, so the same registry works with mock or real backends.
    """

    def __init__(self) -> None:
        self._agents: dict[str, type[BaseAgent]] = {}

    def register(self, agent_cls: type[BaseAgent]) -> type[BaseAgent]:
        """Register an agent class. Returns it, so it can be used as a decorator."""
        name = agent_cls.name
        if name in self._agents:
            raise AgentAlreadyRegisteredError(name)
        self._agents[name] = agent_cls
        return agent_cls

    def create(self, name: str, llm: LLMProvider) -> BaseAgent:
        """Instantiate the named agent with the given LLM provider."""
        try:
            agent_cls = self._agents[name]
        except KeyError as exc:
            raise AgentNotFoundError(name) from exc
        return agent_cls(llm)

    def names(self) -> list[str]:
        """Return the sorted list of registered agent names."""
        return sorted(self._agents)

    def is_registered(self, name: str) -> bool:
        return name in self._agents


#: Process-wide default registry, populated in ``backend.agents.__init__``.
default_registry = AgentRegistry()
