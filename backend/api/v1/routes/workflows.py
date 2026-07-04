from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from backend.api.v1.dependencies import SalesWorkflowServiceDep, WorkflowHistoryServiceDep
from backend.api.v1.schemas.workflow_run import (
    UpdateWorkflowReviewStatusRequest,
    UpdateWorkflowReviewStatusResponse,
    WorkflowRunDetail,
    WorkflowRunListResponse,
    WorkflowRunSummary,
)
from backend.application.workflows.exceptions import WorkflowStepError
from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)
from backend.domain.enums import WorkflowReviewStatus
from backend.domain.exceptions import WorkflowRunNotFoundError

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/sales", response_model=SalesWorkflowResponse)
async def run_sales_workflow(
    payload: SalesWorkflowRequest,
    service: SalesWorkflowServiceDep,
) -> SalesWorkflowResponse:
    """Run the end-to-end sales workflow and return a human-review summary.

    Chains the existing Lead Research, Company Intelligence, Personalization,
    and Email Draft agents in sequence. Analysis and draft only: this
    endpoint never sends an email, contacts the company, or books a meeting.
    Human review and approval remain mandatory before any action is taken.
    The completed run is automatically persisted and can be retrieved later
    via ``GET /workflows/sales/runs/{workflow_id}``.
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
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    company_name: str | None = Query(
        default=None, description="Case-insensitive substring match."
    ),
    review_status: WorkflowReviewStatus | None = Query(default=None),
) -> WorkflowRunListResponse:
    """List persisted sales workflow runs, newest first.

    Read-only: never sends an email, contacts anyone, or books a meeting.
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
) -> WorkflowRunDetail:
    """Retrieve a single persisted sales workflow run, including its full
    input and result payloads. Read-only.
    """
    try:
        run = await history.get_run(workflow_id)
    except WorkflowRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return WorkflowRunDetail.model_validate(run)


@router.patch(
    "/sales/runs/{workflow_id}/review-status",
    response_model=UpdateWorkflowReviewStatusResponse,
)
async def update_sales_workflow_review_status(
    workflow_id: UUID,
    payload: UpdateWorkflowReviewStatusRequest,
    history: WorkflowHistoryServiceDep,
) -> UpdateWorkflowReviewStatusResponse:
    """Change a persisted workflow run's internal review status.

    This is an internal review marker only. Setting ``review_status`` to
    ``approved`` never sends an email, contacts anyone, or books a meeting —
    it means a human has checked the run, nothing more. Any actual outreach
    remains a separate, manual step outside this system.
    """
    try:
        run = await history.update_review_status(workflow_id, payload.review_status)
    except WorkflowRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UpdateWorkflowReviewStatusResponse.model_validate(run)
