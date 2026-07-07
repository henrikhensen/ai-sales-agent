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
    AuditLogServiceDep,
    ComplianceStatusServiceDep,
    DoNotContactServiceDep,
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
from backend.domain.exceptions import DoNotContactEntryNotFoundError
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/compliance", tags=["compliance"])

_compliance_check_rate_limit = rate_limit(
    "compliance_check", "rate_limit_compliance_check_per_minute", 60
)


@router.get("/status", response_model=ComplianceStatusResponse)
async def get_compliance_status(
    service: ComplianceStatusServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> ComplianceStatusResponse:
    """Report a safe, at-a-glance compliance snapshot.

    Read-only, any active admin, sales, or reviewer account. Never returns
    a secret, API key, or token. ``email_sending_enabled`` and
    ``automatic_contact_enabled`` are always ``False`` — there is no
    send/auto-contact capability anywhere in this system.
    """
    status_snapshot = service.get_status()
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
