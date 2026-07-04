"""Exceptions specific to the Lead Research Agent."""

from __future__ import annotations

from backend.agents.exceptions import AgentError


class LeadResearchError(AgentError):
    """Base class for Lead Research Agent errors."""


class InvalidLeadResearchOutputError(LeadResearchError):
    """Raised when the LLM output cannot be parsed into a valid lead profile."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Lead research produced invalid output: {reason}")
