"""Application-level workflows that orchestrate existing agents.

The Sales Workflow chains Lead Research, Company Intelligence,
Personalization, and Email Draft into a single call and produces a
human-review summary. It builds no new agents, sends no email, makes no
contact, and books no meeting — human review and approval remain mandatory.
"""

from backend.application.workflows.exceptions import WorkflowError, WorkflowStepError
from backend.application.workflows.sales_workflow import SalesWorkflowService
from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)

__all__ = [
    "SalesWorkflowRequest",
    "SalesWorkflowResponse",
    "SalesWorkflowService",
    "WorkflowError",
    "WorkflowStepError",
]
