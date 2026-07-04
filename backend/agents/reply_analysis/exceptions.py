"""Exceptions specific to the Reply Analysis Agent."""

from __future__ import annotations

from backend.agents.exceptions import AgentError


class ReplyAnalysisError(AgentError):
    """Base class for Reply Analysis Agent errors."""


class InvalidReplyAnalysisOutputError(ReplyAnalysisError):
    """Raised when the LLM output cannot be parsed into a valid analysis."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Reply analysis produced invalid output: {reason}")
