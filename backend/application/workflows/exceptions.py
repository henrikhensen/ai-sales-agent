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
