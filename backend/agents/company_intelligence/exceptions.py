"""Exceptions specific to the Company Intelligence Agent."""

from __future__ import annotations

from backend.agents.exceptions import AgentError


class CompanyIntelligenceError(AgentError):
    """Base class for Company Intelligence Agent errors."""


class InvalidCompanyIntelligenceOutputError(CompanyIntelligenceError):
    """Raised when the LLM output cannot be parsed into a valid profile."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Company intelligence produced invalid output: {reason}")
