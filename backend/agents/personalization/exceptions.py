"""Exceptions specific to the Personalization Engine."""

from __future__ import annotations

from backend.agents.exceptions import AgentError


class PersonalizationError(AgentError):
    """Base class for Personalization Engine errors."""


class InvalidPersonalizationOutputError(PersonalizationError):
    """Raised when the LLM output cannot be parsed into a valid strategy."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Personalization produced invalid output: {reason}")
