"""Exceptions specific to the Email Draft Agent."""

from __future__ import annotations

from backend.agents.exceptions import AgentError


class EmailDraftError(AgentError):
    """Base class for Email Draft Agent errors."""


class InvalidEmailDraftOutputError(EmailDraftError):
    """Raised when the LLM output cannot be parsed into a valid draft."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Email draft produced invalid output: {reason}")
