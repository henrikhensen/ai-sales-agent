"""Do-not-contact (opt-out) compliance: create, list, update, deactivate, and
check entries.

No endpoint here ever sends an email or contacts anyone — this only ever
manages opt-out records and reports whether a target is blocked. See
``backend.application.workflows.sales_workflow.SalesWorkflowService`` and
``backend.application.reviews.review_service.ReviewService`` for where a
positive check result actually stops outreach preparation and review
approval.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.dependencies.auth import (
    RequireAdminUserDep,
    RequireSalesOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import (
    AdminControlsServiceDep,
    AuditLogRepositoryDep,
    AuditLogServiceDep,
    ComplianceDocumentsServiceDep,
    ComplianceStatusServiceDep,
    DataExportServiceDep,
    DataRequestServiceDep,
    DataRetentionPolicyRepositoryDep,
    DataRetentionRunRepositoryDep,
    DataRetentionServiceDep,
    DoNotContactServiceDep,
)
from backend.application.compliance.compliance_documents_schemas import (
    ComplianceDocumentsResponse,
)
from backend.application.compliance.data_export_schemas import (
    DataExportRequest,
    DataExportResponse,
)
from backend.application.compliance.data_request_schemas import (
    CompleteDataRequestRequest,
    CreateDataSubjectRequestRequest,
    DataSubjectRequestDetailResponse,
    DataSubjectRequestListResponse,
    DataSubjectRequestResponse,
    PrepareAnonymizeDataRequestResponse,
    UpdateDataSubjectRequestRequest,
)
from backend.application.compliance.data_retention_schemas import (
    CreateDataRetentionPolicyRequest,
    DataRetentionPolicyListResponse,
    DataRetentionPolicyResponse,
    DataRetentionRunListResponse,
    DataRetentionRunResponse,
    RunDataRetentionPolicyRequest,
    UpdateDataRetentionPolicyRequest,
)
from backend.application.compliance.schemas import (
    ComplianceStatusResponse,
    CreateDoNotContactRequest,
    DoNotContactCheckRequest,
    DoNotContactCheckResponse,
    DoNotContactEntryResponse,
    DoNotContactListResponse,
    UpdateDoNotContactRequest,
)
from backend.domain.exceptions import (
    DataRetentionPolicyNotFoundError,
    DataRetentionRunNotFoundError,
    DataSubjectRequestNotFoundError,
    DoNotContactEntryNotFoundError,
    InvalidRetentionPolicyError,
    RetentionRunBlockedError,
)
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/compliance", tags=["compliance"])

_compliance_check_rate_limit = rate_limit(
    "compliance_check", "rate_limit_compliance_check_per_minute", 60
)
_compliance_write_rate_limit = Depends(
    rate_limit("compliance_pack_write", "rate_limit_default_per_minute", 60)
)


@router.get("/status", response_model=ComplianceStatusResponse)
async def get_compliance_status(
    service: ComplianceStatusServiceDep,
    admin_controls: AdminControlsServiceDep,
    retention_policies: DataRetentionPolicyRepositoryDep,
    retention_runs: DataRetentionRunRepositoryDep,
    audit_logs: AuditLogRepositoryDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> ComplianceStatusResponse:
    """Report a safe, at-a-glance compliance snapshot.

    Read-only, any active admin, sales, or reviewer account. Never returns
    a secret, API key, or token. ``email_sending_enabled`` and
    ``automatic_contact_enabled`` are always ``False`` — there is no
    send/auto-contact capability anywhere in this system.
    """
    status_snapshot = service.get_status()
    controls = await admin_controls.get_admin_controls()
    policies_count = len(await retention_policies.list(limit=500))
    last_runs = await retention_runs.list(limit=1)
    last_retention_run = last_runs[0].completed_at if last_runs else None
    last_exports = await audit_logs.list_filtered(
        action="data_export_executed", limit=1
    )
    last_data_export_request = last_exports[0].created_at if last_exports else None
    warnings: list[str] = []
    if status_snapshot.llm_real_calls_enabled:
        warnings.append(
            f"Real LLM calls are enabled (provider={status_snapshot.llm_provider})."
        )
    if status_snapshot.email_real_drafts_enabled:
        warnings.append(
            "Real email draft creation is enabled "
            f"(provider={status_snapshot.email_integration_provider})."
        )
    if status_snapshot.reply_real_reads_enabled:
        warnings.append(
            "Real reply reading is enabled "
            f"(provider={status_snapshot.reply_tracking_provider})."
        )
    if not status_snapshot.rate_limits_enabled:
        warnings.append("Rate limits are disabled.")
    if not status_snapshot.audit_logs_enabled:
        warnings.append("Audit logs are disabled.")

    return ComplianceStatusResponse(
        do_not_contact_enabled=status_snapshot.do_not_contact_enabled,
        human_review_enabled=status_snapshot.human_review_enabled,
        email_sending_enabled=status_snapshot.email_sending_enabled,
        automatic_contact_enabled=status_snapshot.automatic_contact_enabled,
        llm_provider=status_snapshot.llm_provider,
        llm_real_calls_enabled=status_snapshot.llm_real_calls_enabled,
        email_integration_provider=status_snapshot.email_integration_provider,
        email_real_drafts_enabled=status_snapshot.email_real_drafts_enabled,
        reply_tracking_provider=status_snapshot.reply_tracking_provider,
        reply_real_reads_enabled=status_snapshot.reply_real_reads_enabled,
        rate_limits_enabled=status_snapshot.rate_limits_enabled,
        audit_logs_enabled=status_snapshot.audit_logs_enabled,
        last_do_not_contact_block_count=status_snapshot.last_do_not_contact_block_count,
        last_review_block_count=status_snapshot.last_review_block_count,
        safe_mode=not (
            status_snapshot.llm_real_calls_enabled
            or status_snapshot.email_real_drafts_enabled
            or status_snapshot.reply_real_reads_enabled
        ),
        warnings=warnings,
        data_retention_enabled=controls.data_retention_enabled,
        data_export_available=controls.data_export_enabled,
        data_requests_enabled=controls.data_subject_requests_enabled,
        legal_review_required=True,
        privacy_notice_available=True,
        data_processing_summary_available=True,
        retention_policies_count=policies_count,
        last_retention_run=last_retention_run,
        last_data_export_request=last_data_export_request,
        message=(
            "No emails are ever sent automatically and no automatic contact "
            "is ever made by this system. Do-not-contact and Human Review "
            "cannot be bypassed."
        ),
    )


@router.get("/do-not-contact", response_model=DoNotContactListResponse)
async def list_do_not_contact_entries(
    service: DoNotContactServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> DoNotContactListResponse:
    """List do-not-contact entries, newest first (active and inactive).

    Read-only, any active admin, sales, or reviewer account.
    """
    return await service.list_entries(limit=limit, offset=offset)


@router.post(
    "/do-not-contact",
    response_model=DoNotContactEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_do_not_contact_entry(
    payload: CreateDoNotContactRequest,
    service: DoNotContactServiceDep,
    current_user: RequireSalesOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> DoNotContactEntryResponse:
    """Create a new do-not-contact entry.

    Requires an active admin or sales account. At least one of ``email``,
    ``domain``, or ``company_name`` is required. Creating an entry never
    sends an email or contacts anyone by itself — it only ever blocks
    future outreach preparation and review approval for the target.
    """
    entry = await service.create_entry(payload, created_by_user_id=current_user.id)
    await audit.record(
        action="do_not_contact_entry_created",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="do_not_contact_entry",
        entity_id=entry.id,
        reason=payload.reason,
        request=request,
    )
    return entry


@router.patch(
    "/do-not-contact/{entry_id}",
    response_model=DoNotContactEntryResponse,
)
async def update_do_not_contact_entry(
    entry_id: UUID,
    payload: UpdateDoNotContactRequest,
    service: DoNotContactServiceDep,
    current_user: RequireAdminUserDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> DoNotContactEntryResponse:
    """Partially update a do-not-contact entry. Admin only.

    Only fields present in the request body are changed.
    """
    try:
        entry = await service.update_entry(entry_id, payload)
    except DoNotContactEntryNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await audit.record(
        action="do_not_contact_entry_updated",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="do_not_contact_entry",
        entity_id=entry_id,
        request=request,
    )
    return entry


@router.patch(
    "/do-not-contact/{entry_id}/deactivate",
    response_model=DoNotContactEntryResponse,
)
async def deactivate_do_not_contact_entry(
    entry_id: UUID,
    service: DoNotContactServiceDep,
    current_user: RequireAdminUserDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> DoNotContactEntryResponse:
    """Deactivate a do-not-contact entry. Admin only.

    An inactive entry no longer blocks anything — it is kept only for audit
    history. This never re-enables outreach automatically; it only stops
    this specific entry from blocking future checks.
    """
    try:
        entry = await service.deactivate_entry(entry_id)
    except DoNotContactEntryNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await audit.record(
        action="do_not_contact_entry_deactivated",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="do_not_contact_entry",
        entity_id=entry_id,
        request=request,
    )
    return entry


@router.post(
    "/do-not-contact/check",
    response_model=DoNotContactCheckResponse,
    dependencies=[Depends(_compliance_check_rate_limit)],
)
async def check_do_not_contact(
    payload: DoNotContactCheckRequest,
    service: DoNotContactServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> DoNotContactCheckResponse:
    """Check an email/domain/company_name against active opt-out entries.

    Read-only, any active admin, sales, or reviewer account. At least one
    of ``email``, ``domain``, or ``company_name`` is required. Never sends
    an email or contacts anyone by itself — it only ever reports whether a
    target is currently blocked. Rate-limited per user
    (``RATE_LIMIT_COMPLIANCE_CHECK_PER_MINUTE``).
    """
    result = await service.check(
        email=payload.email, domain=payload.domain, company_name=payload.company_name
    )
    if result.is_blocked:
        await audit.record(
            action="do_not_contact_check_blocked",
            result="blocked",
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            entity_type="do_not_contact_entry",
            entity_id=result.matched_entry_id,
            reason=result.reason,
            request=request,
        )
    return result


# -- compliance documents ------------------------------------------------------------


@router.get("/documents", response_model=ComplianceDocumentsResponse)
async def get_compliance_documents(
    service: ComplianceDocumentsServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    audit: AuditLogServiceDep,
    request: Request,
) -> ComplianceDocumentsResponse:
    """Return static compliance templates and notices.

    Every document is a template/notice only — never legal advice, never a
    certification of compliance with any law or standard. Any active
    admin, sales, or reviewer account may view these.
    """
    response = service.get_documents()
    await audit.record(
        action="compliance_documents_viewed",
        result="success",
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        entity_type="compliance_documents",
        request=request,
    )
    return response


# -- data retention: policies ---------------------------------------------------------


@router.get(
    "/data-retention/policies", response_model=DataRetentionPolicyListResponse
)
async def list_data_retention_policies(
    service: DataRetentionServiceDep,
    _current_user: RequireAdminUserDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    active_only: bool = Query(default=False),
) -> DataRetentionPolicyListResponse:
    """List data retention policies. Admin only."""
    return await service.list_policies(
        limit=limit, offset=offset, active_only=active_only
    )


@router.post(
    "/data-retention/policies",
    response_model=DataRetentionPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_compliance_write_rate_limit],
)
async def create_data_retention_policy(
    payload: CreateDataRetentionPolicyRequest,
    service: DataRetentionServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> DataRetentionPolicyResponse:
    """Create a data retention policy. Admin only.

    Creating a policy never changes any data by itself — a dry run or a
    confirmed real run must be started separately.
    """
    try:
        return await service.create_policy(
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except InvalidRetentionPolicyError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch(
    "/data-retention/policies/{policy_id}",
    response_model=DataRetentionPolicyResponse,
    dependencies=[_compliance_write_rate_limit],
)
async def update_data_retention_policy(
    policy_id: UUID,
    payload: UpdateDataRetentionPolicyRequest,
    service: DataRetentionServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> DataRetentionPolicyResponse:
    """Partially update a data retention policy. Admin only."""
    try:
        return await service.update_policy(
            policy_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except DataRetentionPolicyNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except InvalidRetentionPolicyError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch(
    "/data-retention/policies/{policy_id}/deactivate",
    response_model=DataRetentionPolicyResponse,
    dependencies=[_compliance_write_rate_limit],
)
async def deactivate_data_retention_policy(
    policy_id: UUID,
    service: DataRetentionServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> DataRetentionPolicyResponse:
    """Deactivate a data retention policy. Admin only.

    A deactivated policy can no longer be run for real (only dry-run
    previewed) until it is reactivated.
    """
    try:
        return await service.deactivate_policy(
            policy_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except DataRetentionPolicyNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/data-retention/policies/{policy_id}/dry-run",
    response_model=DataRetentionRunResponse,
    dependencies=[_compliance_write_rate_limit],
)
async def dry_run_data_retention_policy(
    policy_id: UUID,
    service: DataRetentionServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> DataRetentionRunResponse:
    """Preview a data retention policy. Admin only. Never changes any data."""
    try:
        return await service.dry_run(
            policy_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except DataRetentionPolicyNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/data-retention/policies/{policy_id}/run",
    response_model=DataRetentionRunResponse,
    dependencies=[_compliance_write_rate_limit],
)
async def run_data_retention_policy(
    policy_id: UUID,
    payload: RunDataRetentionPolicyRequest,
    service: DataRetentionServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> DataRetentionRunResponse:
    """Execute a data retention policy for real. Admin only.

    Requires ``confirm=true`` in the request body — an unconfirmed request
    is refused outright. Anonymizes by default; only deletes/archives if
    the policy's ``action`` says so, and only for entity types whose
    repository supports that action. Active do-not-contact entries are
    never touched, regardless of age.
    """
    try:
        return await service.run(
            policy_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except DataRetentionPolicyNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RetentionRunBlockedError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/data-retention/runs", response_model=DataRetentionRunListResponse)
async def list_data_retention_runs(
    service: DataRetentionServiceDep,
    _current_user: RequireAdminUserDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    policy_id: UUID | None = Query(default=None),
) -> DataRetentionRunListResponse:
    """List data retention runs, newest first. Admin only."""
    return await service.list_runs(limit=limit, offset=offset, policy_id=policy_id)


@router.get(
    "/data-retention/runs/{run_id}", response_model=DataRetentionRunResponse
)
async def get_data_retention_run(
    run_id: UUID,
    service: DataRetentionServiceDep,
    _current_user: RequireAdminUserDep,
) -> DataRetentionRunResponse:
    """Return one data retention run's details. Admin only."""
    try:
        return await service.get_run(run_id)
    except DataRetentionRunNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# -- data export ------------------------------------------------------------------------


@router.post(
    "/data-export",
    response_model=DataExportResponse,
    dependencies=[_compliance_write_rate_limit],
)
async def export_compliance_data(
    payload: DataExportRequest,
    service: DataExportServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> DataExportResponse:
    """Search across entities by email/domain/name and export matches.

    Admin only. Read-only — never changes, deletes, or sends anything.
    Never includes a secret, API key, or token. May contain personal data —
    handle the result only for an authorized, legitimate purpose.
    """
    return await service.export(
        payload,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        http_request=request,
    )


# -- data subject requests ---------------------------------------------------------------


@router.get("/data-requests", response_model=DataSubjectRequestListResponse)
async def list_data_requests(
    service: DataRequestServiceDep,
    _current_user: RequireAdminUserDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    request_type: str | None = Query(default=None),
) -> DataSubjectRequestListResponse:
    """List data subject requests, newest first. Admin only."""
    return await service.list_requests(
        limit=limit, offset=offset, status=status_filter, request_type=request_type
    )


@router.post(
    "/data-requests",
    response_model=DataSubjectRequestResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_compliance_write_rate_limit],
)
async def create_data_request(
    payload: CreateDataSubjectRequestRequest,
    service: DataRequestServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> DataSubjectRequestResponse:
    """Record a new data subject request. Admin only.

    Recording a request never performs the requested action automatically
    and never sends an email to the subject.
    """
    return await service.create_request(
        payload,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        http_request=request,
    )


@router.get(
    "/data-requests/{request_id}", response_model=DataSubjectRequestResponse
)
async def get_data_request(
    request_id: UUID,
    service: DataRequestServiceDep,
    _current_user: RequireAdminUserDep,
) -> DataSubjectRequestResponse:
    """Return one data subject request's details. Admin only."""
    try:
        return await service.get_request(request_id)
    except DataSubjectRequestNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/data-requests/{request_id}",
    response_model=DataSubjectRequestResponse,
    dependencies=[_compliance_write_rate_limit],
)
async def update_data_request(
    request_id: UUID,
    payload: UpdateDataSubjectRequestRequest,
    service: DataRequestServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> DataSubjectRequestResponse:
    """Partially update a data subject request. Admin only."""
    try:
        return await service.update_request(
            request_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except DataSubjectRequestNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/data-requests/{request_id}/export",
    response_model=DataSubjectRequestDetailResponse,
    dependencies=[_compliance_write_rate_limit],
)
async def export_data_request(
    request_id: UUID,
    service: DataRequestServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> DataSubjectRequestDetailResponse:
    """Run a data export for this request's subject. Admin only.

    Read-only — never changes, deletes, or sends anything.
    """
    try:
        return await service.export_for_request(
            request_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except DataSubjectRequestNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/data-requests/{request_id}/prepare-anonymize",
    response_model=PrepareAnonymizeDataRequestResponse,
    dependencies=[_compliance_write_rate_limit],
)
async def prepare_anonymize_data_request(
    request_id: UUID,
    service: DataRequestServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> PrepareAnonymizeDataRequestResponse:
    """Identify records that would be affected. Admin only.

    Never anonymizes or deletes anything itself — use Data Retention
    Policies (with explicit confirmation) to actually change data.
    """
    try:
        return await service.prepare_anonymize(
            request_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except DataSubjectRequestNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/data-requests/{request_id}/complete",
    response_model=DataSubjectRequestResponse,
    dependencies=[_compliance_write_rate_limit],
)
async def complete_data_request(
    request_id: UUID,
    payload: CompleteDataRequestRequest,
    service: DataRequestServiceDep,
    current_user: RequireAdminUserDep,
    request: Request,
) -> DataSubjectRequestResponse:
    """Mark a data subject request as completed. Admin only.

    If the request's type is ``do_not_contact``, this also creates a
    do-not-contact entry — it still never contacts anyone; it only ever
    blocks future outreach.
    """
    try:
        return await service.complete_request(
            request_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except DataSubjectRequestNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
