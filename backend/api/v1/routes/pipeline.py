"""CRM Pipeline: board view and lead pipeline-status changes.

Bookkeeping only — no endpoint here ever sends an email, contacts anyone,
or calls an external service. ``pipeline_status=approved`` means only that
a human has internally reviewed the lead's workflow run, never that
anything was sent.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from backend.api.dependencies.auth import RequireSalesReviewerOrAdminDep
from backend.api.v1.dependencies import AuditLogServiceDep, PipelineServiceDep
from backend.application.crm.pipeline_schemas import (
    PipelineBoardResponse,
    UpdateLeadPipelineStatusRequest,
    UpdateLeadPipelineStatusResponse,
)
from backend.domain.enums import PipelineStatus, UserRole
from backend.domain.exceptions import LeadNotFoundError

router = APIRouter(prefix="/crm", tags=["pipeline"])

#: Reviewer accounts may move a lead through the review-adjacent stages
#: only — not the earlier workflow-driven stages (new/research_completed/
#: draft_created) or archiving, which stay a sales/admin concern.
_REVIEWER_ALLOWED_STATUSES = {
    PipelineStatus.IN_REVIEW,
    PipelineStatus.APPROVED,
    PipelineStatus.REJECTED,
}


@router.get("/pipeline", response_model=PipelineBoardResponse)
async def get_pipeline_board(
    service: PipelineServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> PipelineBoardResponse:
    """Return every lead grouped into a column per pipeline status.

    Read-only, any active admin, sales, or reviewer account. Never sends an
    email, contacts anyone, or calls an external service.
    """
    return await service.get_board()


@router.patch(
    "/leads/{lead_id}/pipeline-status",
    response_model=UpdateLeadPipelineStatusResponse,
)
async def update_lead_pipeline_status(
    lead_id: UUID,
    payload: UpdateLeadPipelineStatusRequest,
    service: PipelineServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> UpdateLeadPipelineStatusResponse:
    """Change a lead's pipeline status.

    Admin and sales accounts may set any pipeline status. Reviewer accounts
    may only move a lead to ``in_review``, ``approved``, or ``rejected`` —
    the earlier workflow-driven stages and archiving stay a sales/admin
    concern. This only ever updates bookkeeping fields: it never sends an
    email, contacts anyone, or calls an external service, and ``approved``
    means only that a human has internally reviewed the lead's workflow
    run.
    """
    if (
        current_user.role == UserRole.REVIEWER
        and not current_user.is_superuser
        and payload.pipeline_status not in _REVIEWER_ALLOWED_STATUSES
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=(
                "Reviewer accounts may only set pipeline_status to "
                "'in_review', 'approved', or 'rejected'."
            ),
        )
    try:
        result = await service.update_lead_pipeline_status(
            lead_id, payload.pipeline_status
        )
    except LeadNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    await audit.record(
        action="pipeline_status_changed",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="lead",
        entity_id=lead_id,
        metadata={"pipeline_status": payload.pipeline_status.value},
        request=request,
    )
    return result
