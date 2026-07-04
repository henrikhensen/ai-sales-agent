class AgentError(Exception):
    """Base class for agent framework errors."""


class AgentNotFoundError(AgentError):
    """Raised when an agent name is not registered."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"No agent registered under name '{name}'")


class AgentAlreadyRegisteredError(AgentError):
    """Raised when registering a second agent under an existing name."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"An agent is already registered under name '{name}'")


class AgentOutputValidationError(AgentError):
    """Raised when the LLM output does not conform to the agent's output model."""

    def __init__(self, agent_name: str, reason: str) -> None:
        self.agent_name = agent_name
        self.reason = reason
        super().__init__(
            f"Agent '{agent_name}' produced output that failed validation: {reason}"
        )
