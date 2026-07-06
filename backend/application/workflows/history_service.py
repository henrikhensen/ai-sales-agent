"""Workflow History Service: persists and retrieves workflow runs.

Wraps the :class:`WorkflowRunRepository` port so the API layer never talks to
the ORM or domain entities directly. This service only ever reads and writes
the ``workflow_runs`` table — it never sends an email, never contacts anyone,
and never books a meeting. Changing ``review_status`` to ``approved`` means a
human has internally reviewed the run, nothing more.
"""

from __future__ import annotations

from uuid import UUID

from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)
from backend.domain.entities.workflow_run import WorkflowRun
from backend.domain.enums import WorkflowReviewStatus
from backend.domain.exceptions import WorkflowRunNotFoundError
from backend.domain.repositories.workflow_run_repository import WorkflowRunRepository


class WorkflowHistoryService:
    """Persists sales workflow runs and manages their review lifecycle."""

    def __init__(self, workflow_runs: WorkflowRunRepository) -> None:
        self._workflow_runs = workflow_runs

    async def record_sales_workflow_run(
        self, request: SalesWorkflowRequest, response: SalesWorkflowResponse
    ) -> WorkflowRun:
        """Persist a completed sales workflow run and return the saved record.

        Serializes the request and response as plain JSON-compatible data
        (via Pydantic's JSON mode) — no secrets or API keys are ever part of
        either payload, since neither schema carries credentials.
        """
        run = WorkflowRun(
            company_name=response.company_name,
            workflow_type="sales",
            status=response.status,
            review_status=WorkflowReviewStatus.NEEDS_REVIEW,
            input_payload=request.model_dump(mode="json"),
            result_payload=response.model_dump(mode="json"),
            confidence_score=response.confidence_score,
            missing_information=response.missing_information,
            compliance_notes=response.compliance_notes,
        )
        return await self._workflow_runs.create(run)

    async def get_run(self, run_id: UUID) -> WorkflowRun:
        """Return a single persisted run, or raise if it does not exist."""
        run = await self._workflow_runs.get_by_id(run_id)
        if run is None:
            raise WorkflowRunNotFoundError(run_id)
        return run

    async def list_runs(
        self,
        limit: int = 100,
        offset: int = 0,
        company_name: str | None = None,
        review_status: WorkflowReviewStatus | None = None,
    ) -> list[WorkflowRun]:
        """Return a page of persisted runs, newest first, optionally filtered."""
        return await self._workflow_runs.list(
            limit=limit,
            offset=offset,
            company_name=company_name,
            review_status=review_status,
        )

    async def update_review_status(
        self, run_id: UUID, review_status: WorkflowReviewStatus
    ) -> WorkflowRun:
        """Transition a run's review status, or raise if it does not exist.

        This is an internal review marker only — it never sends an email,
        contacts anyone, or books a meeting, regardless of the new status.
        """
        run = await self._workflow_runs.update_review_status(run_id, review_status)
        if run is None:
            raise WorkflowRunNotFoundError(run_id)
        return run

    async def link_crm_entities(
        self,
        run_id: UUID,
        company_id: UUID | None = None,
        lead_id: UUID | None = None,
        contact_id: UUID | None = None,
        email_draft_id: UUID | None = None,
    ) -> WorkflowRun:
        """Attach CRM entity ids to a persisted run, or raise if it does not exist.

        Purely a bookkeeping link between a workflow run and the CRM records
        it produced (Company, Lead, an optional Contact, and an email
        draft) — it never sends an email, contacts anyone, or books a meeting.
        """
        run = await self._workflow_runs.update_crm_links(
            run_id,
            company_id=company_id,
            lead_id=lead_id,
            contact_id=contact_id,
            email_draft_id=email_draft_id,
        )
        if run is None:
            raise WorkflowRunNotFoundError(run_id)
        return run
