"""Human Review & Approval: audit trail for workflow runs and email drafts.

``ReviewService`` lets a human change an email draft's review status, add a
comment to a workflow run, and read back the resulting audit trail. Every
mutation also writes an immutable :class:`ReviewEvent` record. Nothing here
ever sends an email, contacts anyone, books a meeting, or calls an external
service — ``approved`` means only that a human has internally reviewed the
item, never that it was sent.
"""

from __future__ import annotations

import logging
from uuid import UUID

from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.entities.review_event import ReviewEvent
from backend.domain.enums import EmailDraftReviewStatus, ReviewEventType, WorkflowReviewStatus
from backend.domain.exceptions import (
    DoNotContactBlockedError,
    EmailDraftNotFoundError,
    WorkflowRunNotFoundError,
)
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.domain.repositories.review_event_repository import ReviewEventRepository
from backend.domain.repositories.workflow_run_repository import WorkflowRunRepository
from backend.shared.metrics import increment_review_block_count

logger = logging.getLogger("backend.reviews")

_EVENT_TYPE_FOR_EMAIL_STATUS: dict[EmailDraftReviewStatus, ReviewEventType] = {
    EmailDraftReviewStatus.NEEDS_REVIEW: ReviewEventType.REVIEW_STARTED,
    EmailDraftReviewStatus.IN_REVIEW: ReviewEventType.REVIEW_STARTED,
    EmailDraftReviewStatus.APPROVED: ReviewEventType.APPROVED,
    EmailDraftReviewStatus.REJECTED: ReviewEventType.REJECTED,
    EmailDraftReviewStatus.CHANGES_REQUESTED: ReviewEventType.CHANGES_REQUESTED,
    EmailDraftReviewStatus.ARCHIVED: ReviewEventType.ARCHIVED,
}

_WORKFLOW_STATUS_FOR_EMAIL_STATUS: dict[EmailDraftReviewStatus, WorkflowReviewStatus] = {
    EmailDraftReviewStatus.NEEDS_REVIEW: WorkflowReviewStatus.NEEDS_REVIEW,
    EmailDraftReviewStatus.IN_REVIEW: WorkflowReviewStatus.REVIEWED,
    EmailDraftReviewStatus.APPROVED: WorkflowReviewStatus.APPROVED,
    EmailDraftReviewStatus.REJECTED: WorkflowReviewStatus.REJECTED,
    EmailDraftReviewStatus.CHANGES_REQUESTED: WorkflowReviewStatus.NEEDS_REVIEW,
    EmailDraftReviewStatus.ARCHIVED: WorkflowReviewStatus.ARCHIVED,
}


class ReviewService:
    """Coordinates review status changes, comments, and the audit trail."""

    def __init__(
        self,
        email_drafts: EmailDraftRepository,
        workflow_runs: WorkflowRunRepository,
        review_events: ReviewEventRepository,
        companies: CompanyRepository,
        compliance: DoNotContactService,
    ) -> None:
        self._email_drafts = email_drafts
        self._workflow_runs = workflow_runs
        self._review_events = review_events
        self._companies = companies
        self._compliance = compliance

    async def set_email_draft_review_status(
        self,
        email_draft_id: UUID,
        review_status: EmailDraftReviewStatus,
        reviewer_name: str | None,
        comment: str | None,
    ) -> EmailDraft:
        """Change an email draft's review status and record an audit event.

        If the draft is linked to a workflow run, that run's own
        ``review_status`` is updated to match, so the workflow history view
        stays consistent. Never sends an email or makes contact.

        Opt-out takes precedence over review: approving a draft whose
        company matches an active do-not-contact entry (by domain or
        company name) is refused with :class:`DoNotContactBlockedError` —
        the draft's review status is left unchanged and a ``BLOCKED``
        review event is still recorded for the audit trail. Every other
        transition (including rejecting a blocked draft) is unaffected.
        """
        existing = await self._email_drafts.get(email_draft_id)
        if existing is None:
            raise EmailDraftNotFoundError(email_draft_id)
        # Captured immediately: some repository implementations (e.g. the
        # in-memory test double) return the same mutable object on every
        # `get()` call, so reading this after `update_review_status` would
        # already reflect the new status.
        previous_status = existing.review_status.value

        if review_status == EmailDraftReviewStatus.APPROVED:
            company = await self._companies.get(existing.company_id)
            block = await self._compliance.check(
                domain=company.domain if company else None,
                company_name=company.name if company else None,
            )
            if block.is_blocked:
                increment_review_block_count()
                # create_independent: this call is immediately followed by
                # a raise, which would otherwise roll back the ambient
                # request session (see get_session) and drop the very
                # BLOCKED event this docstring promises gets recorded. A
                # failure recording it must never affect the block itself,
                # so it's swallowed here (mirroring AuditLogService.record)
                # — the DoNotContactBlockedError below always still fires.
                try:
                    await self._review_events.create_independent(
                        ReviewEvent(
                            email_draft_id=email_draft_id,
                            workflow_run_id=existing.workflow_run_id,
                            event_type=ReviewEventType.BLOCKED,
                            previous_status=previous_status,
                            new_status=previous_status,
                            comment=(
                                f"Approval blocked by do-not-contact ({block.matched_by}): "
                                f"{block.reason}"
                            ),
                            reviewer_name=reviewer_name,
                        )
                    )
                except Exception:
                    logger.warning(
                        "failed to record independent BLOCKED review event for "
                        "email_draft_id=%s",
                        email_draft_id,
                        exc_info=True,
                    )
                raise DoNotContactBlockedError(block.matched_by, block.reason)

        updated = await self._email_drafts.update_review_status(
            email_draft_id,
            review_status=review_status,
            reviewer_name=reviewer_name,
            comment=comment,
        )
        if updated is None:
            raise EmailDraftNotFoundError(email_draft_id)

        await self._review_events.create(
            ReviewEvent(
                email_draft_id=email_draft_id,
                workflow_run_id=updated.workflow_run_id,
                event_type=_EVENT_TYPE_FOR_EMAIL_STATUS[review_status],
                previous_status=previous_status,
                new_status=review_status.value,
                comment=comment,
                reviewer_name=reviewer_name,
            )
        )

        if updated.workflow_run_id is not None:
            await self._workflow_runs.update_review_status(
                updated.workflow_run_id,
                _WORKFLOW_STATUS_FOR_EMAIL_STATUS[review_status],
            )

        return updated

    async def list_email_draft_events(self, email_draft_id: UUID) -> list[ReviewEvent]:
        """Return the audit trail for a single email draft, newest first."""
        existing = await self._email_drafts.get(email_draft_id)
        if existing is None:
            raise EmailDraftNotFoundError(email_draft_id)
        return await self._review_events.list_by_email_draft(email_draft_id)

    async def add_workflow_comment(
        self, workflow_run_id: UUID, reviewer_name: str | None, comment: str
    ) -> ReviewEvent:
        """Record a review comment against a workflow run.

        Comment-only: never changes the run's review status and never sends
        an email or makes contact.
        """
        run = await self._workflow_runs.get_by_id(workflow_run_id)
        if run is None:
            raise WorkflowRunNotFoundError(workflow_run_id)

        return await self._review_events.create(
            ReviewEvent(
                workflow_run_id=workflow_run_id,
                event_type=ReviewEventType.COMMENT_ADDED,
                comment=comment,
                reviewer_name=reviewer_name,
            )
        )

    async def list_workflow_events(self, workflow_run_id: UUID) -> list[ReviewEvent]:
        """Return the audit trail for a single workflow run, newest first."""
        run = await self._workflow_runs.get_by_id(workflow_run_id)
        if run is None:
            raise WorkflowRunNotFoundError(workflow_run_id)
        return await self._review_events.list_by_workflow_run(workflow_run_id)
