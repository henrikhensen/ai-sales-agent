from fastapi import APIRouter, HTTPException, status

from backend.api.v1.dependencies import SalesWorkflowServiceDep
from backend.application.workflows.exceptions import WorkflowStepError
from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)

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
    """
    try:
        return await service.run(payload)
    except WorkflowStepError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Sales workflow failed at step '{exc.step}': {exc.reason}",
        ) from exc
