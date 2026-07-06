"""CRM Pipeline Service: the pipeline board and lead pipeline-status changes.

Bookkeeping only — this service never sends an email, never contacts
anyone, and never calls an external service. ``PipelineStatus.APPROVED``
means only that a human has internally reviewed the lead's workflow run;
sending remains a fully separate, manual step outside this system.
"""

from __future__ import annotations

from uuid import UUID

from backend.application.crm.pipeline_schemas import (
    LeadPipelineSummary,
    PipelineBoardResponse,
    PipelineColumn,
    UpdateLeadPipelineStatusResponse,
)
from backend.domain.enums import PipelineStatus, WorkflowReviewStatus
from backend.domain.exceptions import LeadNotFoundError
from backend.domain.repositories.lead_repository import LeadRepository

#: Mirrors a WorkflowRun's approved/rejected review status onto its linked
#: lead's pipeline status. Every other review status leaves the pipeline
#: status untouched — pipeline stage and review status are related but
#: distinct concepts, and only the two terminal review outcomes have an
#: unambiguous pipeline equivalent.
_REVIEW_STATUS_TO_PIPELINE_STATUS: dict[WorkflowReviewStatus, PipelineStatus] = {
    WorkflowReviewStatus.APPROVED: PipelineStatus.APPROVED,
    WorkflowReviewStatus.REJECTED: PipelineStatus.REJECTED,
}


class PipelineService:
    """Loads the CRM pipeline board and changes a lead's pipeline status."""

    def __init__(self, leads: LeadRepository) -> None:
        self._leads = leads

    async def get_board(self) -> PipelineBoardResponse:
        """Return every lead grouped into a column per pipeline status.

        Every :class:`PipelineStatus` gets a column, even an empty one, so
        the board layout stays stable regardless of what leads currently
        exist.
        """
        leads = await self._leads.list_pipeline_board()
        by_status: dict[PipelineStatus, list[LeadPipelineSummary]] = {
            status: [] for status in PipelineStatus
        }
        for lead in leads:
            by_status[lead.pipeline_status].append(
                LeadPipelineSummary.model_validate(lead)
            )

        columns = [
            PipelineColumn(pipeline_status=status, leads=by_status[status])
            for status in PipelineStatus
        ]
        return PipelineBoardResponse(columns=columns)

    async def update_lead_pipeline_status(
        self, lead_id: UUID, pipeline_status: PipelineStatus
    ) -> UpdateLeadPipelineStatusResponse:
        """Transition a lead to ``pipeline_status``.

        Never sends an email or makes contact — this only ever updates the
        lead's own bookkeeping fields (``pipeline_status`` and
        ``pipeline_updated_at``).
        """
        updated = await self._leads.update_pipeline_status(lead_id, pipeline_status)
        if updated is None:
            raise LeadNotFoundError(lead_id)
        return UpdateLeadPipelineStatusResponse.model_validate(updated)

    async def sync_from_workflow_review_status(
        self, lead_id: UUID, review_status: WorkflowReviewStatus
    ) -> None:
        """Best-effort: mirror a workflow run's terminal review status onto
        its linked lead's pipeline status.

        A no-op for any review status other than approved/rejected, and
        silently ignored if the lead no longer exists — this is a secondary
        side effect of reviewing a workflow run, not the primary action, so
        it must never fail the review-status change itself.
        """
        mapped = _REVIEW_STATUS_TO_PIPELINE_STATUS.get(review_status)
        if mapped is None:
            return
        await self._leads.update_pipeline_status(lead_id, mapped)
