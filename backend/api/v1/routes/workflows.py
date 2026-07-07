import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.dependencies.auth import RequireSalesReviewerOrAdminDep
from backend.api.v1.dependencies import (
    AuditLogServiceDep,
    CompanyRepositoryDep,
    ContactRepositoryDep,
    DoNotContactServiceDep,
    PipelineServiceDep,
    SalesWorkflowServiceDep,
    WorkflowHistoryServiceDep,
)
from backend.api.v1.schemas.workflow_run import (
    UpdateWorkflowReviewStatusRequest,
    UpdateWorkflowReviewStatusResponse,
    WorkflowCrmLinksResponse,
    WorkflowRunDetail,
    WorkflowRunListResponse,
    WorkflowRunSummary,
)
from backend.application.workflows.exceptions import (
    WebsiteResearchBlockedError,
    WorkflowStepError,
)
from backend.application.compliance.schemas import DoNotContactCheckResponse
from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)
from backend.domain.entities.workflow_run import WorkflowRun
from backend.domain.enums import UserRole, WorkflowReviewStatus
from backend.domain.exceptions import (
    ICPProfileNotFoundError,
    OfferProfileNotFoundError,
    WorkflowRunNotFoundError,
)
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/workflows", tags=["workflows"])
logger = logging.getLogger("backend.workflows")

_sales_workflow_rate_limit = rate_limit(
    "sales_workflow", "rate_limit_workflow_per_hour", 3600
)

_SALES_BLOCKED_REVIEW_STATUSES = {
    WorkflowReviewStatus.APPROVED,
    WorkflowReviewStatus.REJECTED,
}


async def _do_not_contact_block_for_run(
    run: WorkflowRun,
    companies: CompanyRepositoryDep,
    contacts: ContactRepositoryDep,
    compliance: DoNotContactServiceDep,
) -> DoNotContactCheckResponse:
    """Check whether a workflow run is (or was) blocked by an active opt-out.

    First checks the run's own stored result: a run the Sales Workflow
    already blocked (no email/domain/company_name persisted anywhere else,
    e.g. because no recipient name meant no Contact was created) must stay
    blocked for review purposes too. Otherwise re-checks the run's linked
    company/contact fresh, so an opt-out added *after* a successful run
    still blocks its approval.
    """
    stored_block = (run.result_payload or {}).get("do_not_contact_block")
    if isinstance(stored_block, dict) and stored_block.get("is_blocked"):
        return DoNotContactCheckResponse.model_validate(stored_block)

    company = await companies.get(run.company_id) if run.company_id else None
    contact = await contacts.get(run.contact_id) if run.contact_id else None
    return await compliance.check(
        email=contact.email if contact else None,
        domain=company.domain if company else None,
        company_name=company.name if company else None,
    )


@router.post(
    "/sales",
    response_model=SalesWorkflowResponse,
    dependencies=[Depends(_sales_workflow_rate_limit)],
)
async def run_sales_workflow(
    payload: SalesWorkflowRequest,
    service: SalesWorkflowServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> SalesWorkflowResponse:
    """Run the end-to-end sales workflow and return a human-review summary.

    Requires an active admin, sales, or reviewer account. Chains the
    existing Lead Research, Company Intelligence, Personalization, and
    Email Draft agents in sequence. Analysis and draft only: this endpoint
    never sends an email, contacts the company, or books a meeting. Human
    review and approval remain mandatory before any action is taken. The
    completed run is automatically persisted and can be retrieved later via
    ``GET /workflows/sales/runs/{workflow_id}``. Rate-limited per user
    (``RATE_LIMIT_WORKFLOW_PER_HOUR``).
    """
    await audit.record(
        action="sales_workflow_started",
        result="started",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="company",
        entity_id=payload.company_name,
        metadata={
            "icp_profile_id": (
                str(payload.icp_profile_id) if payload.icp_profile_id else None
            ),
            "offer_profile_id": (
                str(payload.offer_profile_id) if payload.offer_profile_id else None
            ),
        },
        request=request,
    )
    try:
        result = await service.run(payload)
    except (ICPProfileNotFoundError, OfferProfileNotFoundError) as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except WebsiteResearchBlockedError as exc:
        # Security-relevant rejection (blocked/invalid URL) — log the
        # internal reason for operators, but never echo it to the client.
        logger.warning("website research request blocked: %s", exc.reason)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The requested website could not be researched: the URL is not permitted.",
        ) from exc
    except WorkflowStepError as exc:
        await audit.record(
            action="sales_workflow_completed",
            result="failed",
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            entity_type="company",
            entity_id=payload.company_name,
            reason=f"step={exc.step}",
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Sales workflow failed at step '{exc.step}': {exc.reason}",
        ) from exc

    if result.status == "blocked":
        await audit.record(
            action="sales_workflow_blocked",
            result="blocked",
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            entity_type="workflow_run",
            entity_id=result.workflow_id,
            reason="do-not-contact match",
            request=request,
        )
    else:
        await audit.record(
            action="sales_workflow_completed",
            result="success",
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            entity_type="workflow_run",
            entity_id=result.workflow_id,
            request=request,
        )
        if result.crm_email_draft_id is not None:
            await audit.record(
                action="email_draft_created",
                result="success",
                actor_user_id=current_user.id,
                actor_role=current_user.role.value,
                entity_type="email_draft",
                entity_id=result.crm_email_draft_id,
                request=request,
            )
    return result


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
    pipeline: PipelineServiceDep,
    companies: CompanyRepositoryDep,
    contacts: ContactRepositoryDep,
    compliance: DoNotContactServiceDep,
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

    Opt-out takes precedence over review: setting ``approved`` is refused
    with a 409 if the run's linked company, contact email, or company
    domain matches an active do-not-contact entry.

    If the run is linked to a CRM lead, an ``approved``/``rejected``
    review status is also mirrored onto that lead's CRM Pipeline status
    (see ``GET /crm/pipeline``) — again bookkeeping only, never a trigger
    for sending anything.
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
        if payload.review_status == WorkflowReviewStatus.APPROVED:
            existing_run = await history.get_run(workflow_id)
            block = await _do_not_contact_block_for_run(
                existing_run, companies, contacts, compliance
            )
            if block.is_blocked:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    detail=(
                        "This workflow run cannot be approved: it matches an "
                        f"active do-not-contact entry (matched by "
                        f"{block.matched_by}). Do-not-contact takes "
                        "precedence over review approval."
                    ),
                )
        run = await history.update_review_status(workflow_id, payload.review_status)
    except WorkflowRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    if run.lead_id is not None:
        await pipeline.sync_from_workflow_review_status(
            run.lead_id, payload.review_status
        )

    return UpdateWorkflowReviewStatusResponse.model_validate(run)
