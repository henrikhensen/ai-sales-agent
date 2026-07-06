"""Exceptions specific to application-level workflows."""

from __future__ import annotations


class WorkflowError(Exception):
    """Base class for workflow orchestration errors."""


class WorkflowStepError(WorkflowError):
    """Raised when a single step of a workflow fails."""

    def __init__(self, step: str, reason: str) -> None:
        self.step = step
        self.reason = reason
        super().__init__(f"Workflow step '{step}' failed: {reason}")


class WebsiteResearchBlockedError(WorkflowError):
    """Raised when website research was requested for a URL the fetcher
    refuses to touch (blocked host, private/internal address, invalid
    scheme, etc.).

    This is a security-relevant rejection, not an ordinary fetch failure
    (timeout, HTTP error, ...) — those are recorded as a warning and the
    workflow continues. Callers should surface this as a clean, generic
    error (e.g. HTTP 400) without echoing ``reason`` to the client; it may
    contain details (like which host was blocked) only meant for logs.
    """

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Website research request was blocked: {reason}")
