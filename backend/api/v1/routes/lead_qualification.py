"""Lead Qualification & Scoring: scores and prioritizes Lead Candidates
and CRM Leads for human review.

Pure scoring and recommendation endpoints — nothing here sends an email,
contacts anyone, starts a Sales Workflow, or creates a draft. A
qualification result is a recommendation only, never a record that
outreach happened.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.dependencies.auth import (
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import AuditLogServiceDep, LeadQualificationServiceDep
from backend.application.lead_qualification.schemas import (
    LeadQualificationStatusResponse,
    QualificationDashboardResponse,
    QualificationResultListResponse,
    QualificationResultResponse,
    QualificationReviewRequest,
    QualificationReviewResponse,
    QualificationRunListResponse,
    QualificationRunResponse,
    QualifyCRMLeadRequest,
    QualifyLeadCandidateRequest,
    StartLeadQualificationRequest,
    StartLeadQualificationResponse,
)
from backend.domain.exceptions import (
    ICPRequiredForQualificationError,
    LeadCandidateNotFoundError,
    QualificationResultNotFoundError,
    QualificationRunNotFoundError,
    QualificationTargetNotFoundError,
)
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/lead-qualification", tags=["lead-qualification"])

_qualification_rate_limit = Depends(
    rate_limit("lead_qualification", "rate_limit_lead_qualification_per_hour", 3600)
)


@router.get("/status", response_model=LeadQualificationStatusResponse)
async def get_status(
    service: LeadQualificationServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> LeadQualificationStatusResponse:
    """Report whether qualification is enabled, safe-mode LLM status, and
    current thresholds. Read-only, any active admin, sales, or reviewer
    account."""
    return await service.get_status()


@router.get("/dashboard", response_model=QualificationDashboardResponse)
async def get_dashboard(
    service: LeadQualificationServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> QualificationDashboardResponse:
    return await service.get_dashboard()


# -- runs ------------------------------------------------------------------------


@router.post(
    "/runs",
    response_model=StartLeadQualificationResponse,
    dependencies=[_qualification_rate_limit],
)
async def start_run(
    payload: StartLeadQualificationRequest,
    service: LeadQualificationServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> StartLeadQualificationResponse:
    """Start a qualification run over a batch of Lead Candidates and/or CRM
    Leads. Never sends an email, contacts anyone, or starts a Sales
    Workflow — it only ever scores and prioritizes. Rate-limited per user
    (``RATE_LIMIT_LEAD_QUALIFICATION_PER_HOUR``).
    """
    try:
        return await service.start_run(
            payload,
            started_by_user_id=current_user.id,
            started_by_role=current_user.role.value,
            http_request=request,
        )
    except ICPRequiredForQualificationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/runs", response_model=QualificationRunListResponse)
async def list_runs(
    service: LeadQualificationServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> QualificationRunListResponse:
    return await service.list_runs(limit=limit, offset=offset)


@router.get("/runs/{run_id}", response_model=QualificationRunResponse)
async def get_run(
    run_id: UUID,
    service: LeadQualificationServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> QualificationRunResponse:
    try:
        return await service.get_run(run_id)
    except QualificationRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# -- results ----------------------------------------------------------------------


@router.get("/results", response_model=QualificationResultListResponse)
async def list_results(
    service: LeadQualificationServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    qualification_run_id: UUID | None = Query(default=None),
    qualification_status: str | None = Query(default=None),
) -> QualificationResultListResponse:
    return await service.list_results(
        limit=limit,
        offset=offset,
        qualification_run_id=qualification_run_id,
        qualification_status=qualification_status,
    )


@router.get("/results/{result_id}", response_model=QualificationResultResponse)
async def get_result(
    result_id: UUID,
    service: LeadQualificationServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> QualificationResultResponse:
    try:
        return await service.get_result(result_id)
    except QualificationResultNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# -- single-item qualify ------------------------------------------------------------


@router.post(
    "/candidates/{candidate_id}/qualify",
    response_model=QualificationResultResponse,
    dependencies=[_qualification_rate_limit],
)
async def qualify_lead_candidate(
    candidate_id: UUID,
    payload: QualifyLeadCandidateRequest,
    service: LeadQualificationServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> QualificationResultResponse:
    try:
        return await service.qualify_lead_candidate(
            candidate_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except LeadCandidateNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ICPRequiredForQualificationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/leads/{lead_id}/qualify",
    response_model=QualificationResultResponse,
    dependencies=[_qualification_rate_limit],
)
async def qualify_crm_lead(
    lead_id: UUID,
    payload: QualifyCRMLeadRequest,
    service: LeadQualificationServiceDep,
    current_user: RequireSalesOrAdminDep,
    request: Request,
) -> QualificationResultResponse:
    try:
        return await service.qualify_crm_lead(
            lead_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except QualificationTargetNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ICPRequiredForQualificationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# -- review -----------------------------------------------------------------------


@router.patch("/results/{result_id}/review", response_model=QualificationReviewResponse)
async def review_result(
    result_id: UUID,
    payload: QualificationReviewRequest,
    service: LeadQualificationServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    request: Request,
) -> QualificationReviewResponse:
    """Manually confirm/override a qualification result's status.

    Do-not-contact can never be bypassed: a blocked result stays blocked
    regardless of the reviewer's chosen status.
    """
    try:
        return await service.review_result(
            result_id,
            payload,
            reviewed_by_user_id=current_user.id,
            reviewed_by_role=current_user.role.value,
            http_request=request,
        )
    except QualificationResultNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
