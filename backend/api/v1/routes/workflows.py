from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from backend.api.dependencies.auth import RequireSalesReviewerOrAdminDep
from backend.api.v1.dependencies import SalesWorkflowServiceDep, WorkflowHistoryServiceDep
from backend.api.v1.schemas.workflow_run import (
    UpdateWorkflowReviewStatusRequest,
    UpdateWorkflowReviewStatusResponse,
    WorkflowCrmLinksResponse,
    WorkflowRunDetail,
    WorkflowRunListResponse,
    WorkflowRunSummary,
)
from backend.application.workflows.exceptions import WorkflowStepError
from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)
from backend.domain.enums import UserRole, WorkflowReviewStatus
from backend.domain.exceptions import WorkflowRunNotFoundError

router = APIRouter(prefix="/workflows", tags=["workflows"])

_SALES_BLOCKED_REVIEW_STATUSES = {
    WorkflowReviewStatus.APPROVED,
    WorkflowReviewStatus.REJECTED,
}


@router.post("/sales", response_model=SalesWorkflowResponse)
async def run_sales_workflow(
    payload: SalesWorkflowRequest,
    service: SalesWorkflowServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> SalesWorkflowResponse:
    """Run the end-to-end sales workflow and return a human-review summary.

    Requires an active admin, sales, or reviewer account. Chains the
    existing Lead Research, Company Intelligence, Personalization, and
    Email Draft agents in sequence. Analysis and draft only: this endpoint
    never sends an email, contacts the company, or books a meeting. Human
    review and approval remain mandatory before any action is taken. The
    completed run is automatically persisted and can be retrieved later via
    ``GET /workflows/sales/runs/{workflow_id}``.
    """
    try:
        return await service.run(payload)
    except WorkflowStepError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Sales workflow failed at step '{exc.step}': {exc.reason}",
        ) from exc


@router.get("/sales/runs", response_model=WorkflowRunListResponse)
async def list_sales_workflow_runs(
    history: WorkflowHistoryServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    company_name: str | None = Query(
        default=None, description="Case-insensitive substring match."
    ),
    review_status: WorkflowReviewStatus | None = Query(default=None),
) -> WorkflowRunListResponse:
    """List persisted sales workflow runs, newest first.

    Read-only, any active admin, sales, or reviewer account: never sends an
    email, contacts anyone, or books a meeting.
    """
    runs = await history.list_runs(
        limit=limit,
        offset=offset,
        company_name=company_name,
        review_status=review_status,
    )
    return WorkflowRunListResponse(
        items=[WorkflowRunSummary.model_validate(run) for run in runs],
        limit=limit,
        offset=offset,
    )


@router.get("/sales/runs/{workflow_id}", response_model=WorkflowRunDetail)
async def get_sales_workflow_run(
    workflow_id: UUID,
    history: WorkflowHistoryServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> WorkflowRunDetail:
    """Retrieve a single persisted sales workflow run, including its full
    input and result payloads. Read-only, any active admin, sales, or
    reviewer account.
    """
    try:
        run = await history.get_run(workflow_id)
    except WorkflowRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return WorkflowRunDetail.model_validate(run)


@router.get(
    "/sales/runs/{workflow_id}/crm-links",
    response_model=WorkflowCrmLinksResponse,
)
async def get_sales_workflow_crm_links(
    workflow_id: UUID,
    history: WorkflowHistoryServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> WorkflowCrmLinksResponse:
    """Return the CRM entity ids a persisted workflow run was linked to.

    Read-only, any active admin, sales, or reviewer account: never sends
    an email, contacts anyone, or books a meeting.
    """
    try:
        run = await history.get_run(workflow_id)
    except WorkflowRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return WorkflowCrmLinksResponse(
        workflow_id=run.id,
        company_id=run.company_id,
        lead_id=run.lead_id,
        contact_id=run.contact_id,
        email_draft_id=run.email_draft_id,
    )


@router.patch(
    "/sales/runs/{workflow_id}/review-status",
    response_model=UpdateWorkflowReviewStatusResponse,
)
async def update_sales_workflow_review_status(
    workflow_id: UUID,
    payload: UpdateWorkflowReviewStatusRequest,
    history: WorkflowHistoryServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
) -> UpdateWorkflowReviewStatusResponse:
    """Change a persisted workflow run's internal review status.

    Admin and reviewer accounts may set any review status. Sales accounts
    may use this endpoint too, but may not set ``approved`` or
    ``rejected`` — those two transitions require an admin or reviewer.
    This is an internal review marker only either way. Setting
    ``review_status`` to ``approved`` never sends an email, contacts
    anyone, or books a meeting — it means a human has checked the run,
    nothing more. Any actual outreach remains a separate, manual step
    outside this system.
    """
    if (
        current_user.role == UserRole.SALES
        and not current_user.is_superuser
        and payload.review_status in _SALES_BLOCKED_REVIEW_STATUSES
    ):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=(
                "Sales accounts may not set review_status to "
                f"'{payload.review_status.value}'; an admin or reviewer "
                "account is required for that transition."
            ),
        )
    try:
        run = await history.update_review_status(workflow_id, payload.review_status)
    except WorkflowRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UpdateWorkflowReviewStatusResponse.model_validate(run)
