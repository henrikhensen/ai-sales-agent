"""Controlled Outreach Dispatch: processes a single, already-approved
Outreach Queue item into either a controlled external draft, or — only
when explicitly enabled and confirmed by a human — a manually confirmed
send.

There is no automatic or batch sending anywhere in this service: every
action operates on exactly one queue item, requires an existing approved
email draft, and (beyond a pure readiness check) requires an explicit
compliance acknowledgement and final confirmation from a human before any
provider action is attempted. Do-not-contact and Human Review approval are
re-verified immediately before every provider call and can never be
bypassed — see :class:`~backend.application.outreach.dispatch_readiness_service.DispatchReadinessService`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.integrations.email_draft_integration_service import (
    EmailDraftIntegrationService,
)
from backend.application.outreach.dispatch_readiness_service import (
    DispatchReadinessService,
)
from backend.application.outreach.dispatch_schemas import (
    CancelDispatchRequest,
    CancelDispatchResponse,
    ConfirmDispatchRequest,
    ConfirmDispatchResponse,
    CreateDispatchRequest,
    CreateDispatchResponse,
    DispatchComplianceAckRequest,
    DispatchComplianceAckResponse,
    DispatchDashboardResponse,
    DispatchReadinessCheckRequest,
    DispatchReadinessCheckResponse,
    OutreachDispatchListResponse,
    OutreachDispatchResponse,
)
from backend.application.outreach.outreach_queue_service import OutreachQueueService
from backend.application.outreach.schemas import UpdateQueueItemStatusRequest
from backend.domain.entities.outreach_dispatch import OutreachDispatch
from backend.domain.entities.outreach_queue_item import OutreachQueueItem
from backend.domain.exceptions import (
    InvalidOutreachQueueStatusTransitionError,
    OutreachDispatchBlockedError,
    OutreachDispatchNotFoundError,
    OutreachDispatchNotReadyError,
    OutreachQueueItemBlockedError,
    OutreachQueueItemNotFoundError,
)
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.domain.repositories.outreach_dispatch_repository import (
    OutreachDispatchRepository,
)
from backend.domain.repositories.outreach_queue_item_repository import (
    OutreachQueueItemRepository,
)
from backend.infrastructure.dispatch.base import DispatchProvider
from backend.infrastructure.dispatch.factory import create_dispatch_provider
from backend.shared.config import Settings

#: Dispatch statuses from which no further action is possible.
_TERMINAL_DISPATCH_STATUSES = frozenset(
    {"cancelled", "failed", "archived", "sent_manually_confirmed", "external_draft_created"}
)

_SUBJECT_SNAPSHOT_MAX_CHARS = 200
_BODY_PREVIEW_SNAPSHOT_MAX_CHARS = 280


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OutreachDispatchService:
    def __init__(
        self,
        dispatches: OutreachDispatchRepository,
        queue_items: OutreachQueueItemRepository,
        email_drafts: EmailDraftRepository,
        connections: EmailProviderConnectionRepository,
        email_draft_integration: EmailDraftIntegrationService,
        outreach_queue_service: OutreachQueueService,
        readiness: DispatchReadinessService,
        compliance: DoNotContactService,
        audit: AuditLogService,
        settings: Settings,
    ) -> None:
        self._dispatches = dispatches
        self._queue_items = queue_items
        self._email_drafts = email_drafts
        self._connections = connections
        self._email_draft_integration = email_draft_integration
        self._outreach_queue_service = outreach_queue_service
        self._readiness = readiness
        self._compliance = compliance
        self._audit = audit
        self._settings = settings

    def _build_provider(self) -> DispatchProvider:
        return create_dispatch_provider(
            self._connections, self._email_draft_integration, self._settings
        )

    # -- dashboard ----------------------------------------------------------------

    async def get_dashboard(self) -> DispatchDashboardResponse:
        sample = await self._dispatches.list(limit=1000)

        def _count(status: str) -> int:
            return sum(1 for d in sample if d.dispatch_status == status)

        warnings: list[str] = []
        if not self._settings.outreach_dispatch_enabled:
            warnings.append(
                "Controlled Outreach Dispatch is disabled (OUTREACH_DISPATCH_ENABLED=false)."
            )
        if self._settings.outreach_dispatch_mode == "manual_send":
            warnings.append(
                "Dispatch mode is 'manual_send' — a real send is only ever "
                "attempted after readiness, compliance acknowledgement, and "
                "final confirmation, and only for the mock provider (Gmail/"
                "Outlook never implement real sending in this build)."
            )
        if self._settings.outreach_dispatch_enable_real_send:
            warnings.append(
                "OUTREACH_DISPATCH_ENABLE_REAL_SEND=true — manual_send "
                "dispatches may be attempted against the configured provider."
            )
        else:
            warnings.append(
                "Real send is disabled (OUTREACH_DISPATCH_ENABLE_REAL_SEND=false) "
                "— every dispatch stays draft-only regardless of mode."
            )

        return DispatchDashboardResponse(
            enabled=self._settings.outreach_dispatch_enabled,
            dispatch_mode=self._settings.outreach_dispatch_mode,
            provider=self._settings.outreach_dispatch_provider,
            real_send_enabled=self._settings.outreach_dispatch_enable_real_send,
            require_final_confirmation=self._settings.outreach_dispatch_require_final_confirmation,
            require_compliance_ack=self._settings.outreach_dispatch_require_compliance_ack,
            require_approved_review=self._settings.outreach_dispatch_require_approved_review,
            require_do_not_contact_check=self._settings.outreach_dispatch_require_do_not_contact_check,
            max_per_day=self._settings.outreach_dispatch_max_per_day,
            max_per_hour=self._settings.outreach_dispatch_max_per_hour,
            total_pending=_count("pending"),
            total_blocked=_count("blocked"),
            total_ready=_count("ready"),
            total_external_draft_created=_count("external_draft_created"),
            total_send_ready=_count("send_ready"),
            total_sent_manually_confirmed=_count("sent_manually_confirmed"),
            total_failed=_count("failed"),
            total_cancelled=_count("cancelled"),
            warnings=warnings,
        )

    # -- readiness ------------------------------------------------------------------

    async def check_readiness(
        self,
        queue_item_id: UUID,
        request: DispatchReadinessCheckRequest,
        actor_user_id: UUID | None,
    ) -> DispatchReadinessCheckResponse:
        queue_item = await self._queue_items.get_by_id(queue_item_id)
        if queue_item is None:
            raise OutreachQueueItemNotFoundError(queue_item_id)

        dispatch_mode = request.dispatch_mode or self._settings.outreach_dispatch_mode
        provider = self._build_provider()
        existing = await self._dispatches.find_active_for_queue_item(queue_item_id)
        return await self._readiness.check(
            queue_item,
            dispatch_mode=dispatch_mode,
            provider=provider,
            existing_dispatch=existing,
            actor_user_id=actor_user_id,
        )

    # -- create -----------------------------------------------------------------------

    async def create_dispatch(
        self,
        queue_item_id: UUID,
        request: CreateDispatchRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> CreateDispatchResponse:
        queue_item = await self._queue_items.get_by_id(queue_item_id)
        if queue_item is None:
            raise OutreachQueueItemNotFoundError(queue_item_id)

        existing = await self._dispatches.find_active_for_queue_item(queue_item_id)
        dispatch_mode = request.dispatch_mode or self._settings.outreach_dispatch_mode
        provider = self._build_provider()

        if existing is not None:
            readiness = await self._readiness.check(
                queue_item,
                dispatch_mode=existing.dispatch_mode,
                provider=provider,
                existing_dispatch=existing,
                actor_user_id=actor_user_id,
            )
            return CreateDispatchResponse(
                dispatch=OutreachDispatchResponse.model_validate(existing),
                readiness=readiness,
            )

        readiness = await self._readiness.check(
            queue_item,
            dispatch_mode=dispatch_mode,
            provider=provider,
            existing_dispatch=None,
            actor_user_id=actor_user_id,
        )

        recipient_email, _domain, _company_name = (
            await self._readiness.resolve_recipient_context(queue_item)
        )
        subject_snapshot, body_preview_snapshot = await self._snapshot_draft(
            queue_item.email_draft_id
        )

        now = _now()
        dispatch = await self._dispatches.create(
            OutreachDispatch(
                queue_item_id=queue_item_id,
                outreach_campaign_id=queue_item.campaign_id,
                lead_id=queue_item.lead_id,
                company_id=queue_item.company_id,
                email_draft_id=queue_item.email_draft_id,
                review_id=queue_item.review_id,
                provider=provider.name,
                dispatch_mode=dispatch_mode,
                dispatch_status="pending" if readiness.is_ready else "blocked",
                recipient_email=recipient_email,
                subject_snapshot=subject_snapshot,
                body_preview_snapshot=body_preview_snapshot,
                do_not_contact_checked_at=now,
                human_review_checked_at=now,
                last_error="; ".join(readiness.blockers) if readiness.blockers else None,
                created_by_user_id=actor_user_id,
            )
        )

        await self._audit.record(
            action="outreach_dispatch_created",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_dispatch",
            entity_id=dispatch.id,
            metadata={
                "queue_item_id": str(queue_item_id),
                "dispatch_mode": dispatch_mode,
                "is_ready": readiness.is_ready,
            },
            request=http_request,
        )
        if readiness.blockers:
            await self._audit_blockers(
                dispatch, readiness.blockers, actor_user_id, actor_role, http_request
            )

        return CreateDispatchResponse(
            dispatch=OutreachDispatchResponse.model_validate(dispatch),
            readiness=readiness,
        )

    async def _snapshot_draft(
        self, email_draft_id: UUID | None
    ) -> tuple[str | None, str | None]:
        if email_draft_id is None:
            return None, None
        draft = await self._email_drafts.get(email_draft_id)
        if draft is None:
            return None, None
        subject = draft.subject_lines[0] if draft.subject_lines else None
        subject_snapshot = subject[:_SUBJECT_SNAPSHOT_MAX_CHARS] if subject else None
        body_preview_snapshot = None
        if draft.email_body:
            preview = draft.email_body[:_BODY_PREVIEW_SNAPSHOT_MAX_CHARS]
            if len(draft.email_body) > _BODY_PREVIEW_SNAPSHOT_MAX_CHARS:
                preview += "…"
            body_preview_snapshot = preview
        return subject_snapshot, body_preview_snapshot

    async def _audit_blockers(
        self,
        dispatch: OutreachDispatch,
        blockers: list[str],
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None,
    ) -> None:
        joined = " ".join(blockers).lower()
        if "do-not-contact" in joined:
            action = "outreach_dispatch_blocked_do_not_contact"
        elif "review" in joined:
            action = "outreach_dispatch_blocked_review"
        elif "limit" in joined:
            action = "outreach_dispatch_blocked_rate_limit"
        elif "provider" in joined or "config" in joined:
            action = "outreach_dispatch_blocked_config"
        else:
            action = "outreach_dispatch_blocked"
        await self._audit.record(
            action=action,
            result="blocked",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_dispatch",
            entity_id=dispatch.id,
            reason="; ".join(blockers),
            request=http_request,
        )

    # -- listing ----------------------------------------------------------------------

    async def list_dispatches(
        self,
        limit: int = 100,
        offset: int = 0,
        queue_item_id: UUID | None = None,
        dispatch_status: str | None = None,
    ) -> OutreachDispatchListResponse:
        dispatches = await self._dispatches.list(
            limit=limit, offset=offset, queue_item_id=queue_item_id, dispatch_status=dispatch_status
        )
        return OutreachDispatchListResponse(
            items=[OutreachDispatchResponse.model_validate(d) for d in dispatches],
            limit=limit,
            offset=offset,
        )

    async def get_dispatch(self, dispatch_id: UUID) -> OutreachDispatchResponse:
        dispatch = await self._dispatches.get_by_id(dispatch_id)
        if dispatch is None:
            raise OutreachDispatchNotFoundError(dispatch_id)
        return OutreachDispatchResponse.model_validate(dispatch)

    async def _get_or_404(self, dispatch_id: UUID) -> OutreachDispatch:
        dispatch = await self._dispatches.get_by_id(dispatch_id)
        if dispatch is None:
            raise OutreachDispatchNotFoundError(dispatch_id)
        return dispatch

    # -- compliance ack -----------------------------------------------------------------

    async def acknowledge_compliance(
        self,
        dispatch_id: UUID,
        request: DispatchComplianceAckRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> DispatchComplianceAckResponse:
        dispatch = await self._get_or_404(dispatch_id)
        if dispatch.dispatch_status in _TERMINAL_DISPATCH_STATUSES:
            raise OutreachDispatchNotReadyError(
                [f"Dispatch is already '{dispatch.dispatch_status}' and cannot be acknowledged."]
            )

        if not all(
            (
                request.contact_permission_confirmed,
                request.do_not_contact_confirmed,
                request.human_review_confirmed,
                request.draft_or_controlled_send_confirmed,
                request.legal_responsibility_confirmed,
            )
        ):
            raise OutreachDispatchBlockedError(
                "compliance_ack_incomplete",
                "Every compliance statement must be confirmed before "
                "acknowledgement can be recorded.",
            )

        dispatch.compliance_acknowledged_by_user_id = actor_user_id
        dispatch.compliance_acknowledged_at = _now()

        queue_item = await self._queue_items.get_by_id(dispatch.queue_item_id)
        if queue_item is not None and dispatch.dispatch_status != "blocked":
            readiness = await self._readiness.check(
                queue_item,
                dispatch_mode=dispatch.dispatch_mode,
                provider=self._build_provider(),
                existing_dispatch=dispatch,
                actor_user_id=actor_user_id,
            )
            dispatch.dispatch_status = "ready" if readiness.is_ready else "blocked"
            dispatch.last_error = (
                "; ".join(readiness.blockers) if readiness.blockers else None
            )

        updated = await self._dispatches.update(dispatch)
        assert updated is not None

        await self._audit.record(
            action="outreach_compliance_ack_set",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_dispatch",
            entity_id=dispatch_id,
            request=http_request,
        )
        return DispatchComplianceAckResponse(
            dispatch=OutreachDispatchResponse.model_validate(updated)
        )

    # -- confirm ------------------------------------------------------------------------

    async def confirm(
        self,
        dispatch_id: UUID,
        request: ConfirmDispatchRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> ConfirmDispatchResponse:
        dispatch = await self._get_or_404(dispatch_id)
        if dispatch.dispatch_status in _TERMINAL_DISPATCH_STATUSES:
            raise OutreachDispatchNotReadyError(
                [f"Dispatch is already '{dispatch.dispatch_status}' and cannot be confirmed again."]
            )

        queue_item = await self._queue_items.get_by_id(dispatch.queue_item_id)
        if queue_item is None:
            dispatch.dispatch_status = "failed"
            dispatch.last_error = "The underlying queue item no longer exists."
            await self._dispatches.update(dispatch)
            raise OutreachQueueItemNotFoundError(dispatch.queue_item_id)

        dispatch.final_confirmation_by_user_id = actor_user_id
        dispatch.final_confirmation_at = _now()

        provider = self._build_provider()
        readiness = await self._readiness.check(
            queue_item,
            dispatch_mode=dispatch.dispatch_mode,
            provider=provider,
            existing_dispatch=dispatch,
            actor_user_id=actor_user_id,
        )

        if not readiness.is_ready:
            dispatch.dispatch_status = "blocked"
            dispatch.last_error = "; ".join(readiness.blockers)
            await self._dispatches.update(dispatch)
            await self._audit_blockers(
                dispatch, readiness.blockers, actor_user_id, actor_role, http_request
            )
            raise OutreachDispatchBlockedError(
                "readiness_failed", "; ".join(readiness.blockers)
            )

        warnings = list(readiness.warnings)

        if dispatch.dispatch_mode == "manual_send":
            await self._execute_manual_send(
                dispatch, provider, actor_user_id, actor_role, http_request
            )
        else:
            await self._execute_external_draft(
                dispatch, provider, actor_user_id, actor_role, http_request
            )

        updated = await self._dispatches.update(dispatch)
        assert updated is not None
        return ConfirmDispatchResponse(
            dispatch=OutreachDispatchResponse.model_validate(updated), warnings=warnings
        )

    async def _execute_external_draft(
        self,
        dispatch: OutreachDispatch,
        provider: DispatchProvider,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None,
    ) -> None:
        if dispatch.email_draft_id is None:
            dispatch.dispatch_status = "failed"
            dispatch.last_error = "No email draft is linked to this dispatch."
            return

        result = await provider.create_external_draft(
            user_id=actor_user_id or dispatch.created_by_user_id,
            email_draft_id=dispatch.email_draft_id,
        )
        if result.blocked:
            dispatch.dispatch_status = "blocked"
            dispatch.last_error = result.message
            await self._audit.record(
                action="outreach_dispatch_blocked",
                result="blocked",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="outreach_dispatch",
                entity_id=dispatch.id,
                reason=result.message,
                request=http_request,
            )
            return

        dispatch.dispatch_status = "external_draft_created"
        dispatch.provider_draft_id = result.provider_draft_id
        dispatch.provider_url = result.provider_url
        dispatch.last_error = None

        await self._advance_queue_item(
            dispatch, "external_draft_created", actor_user_id, actor_role, http_request
        )
        await self._audit.record(
            action="outreach_external_draft_created_from_dispatch",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_dispatch",
            entity_id=dispatch.id,
            request=http_request,
        )

    async def _execute_manual_send(
        self,
        dispatch: OutreachDispatch,
        provider: DispatchProvider,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None,
    ) -> None:
        if not self._settings.outreach_dispatch_enable_real_send:
            dispatch.dispatch_status = "blocked"
            dispatch.last_error = (
                "Real send is disabled (OUTREACH_DISPATCH_ENABLE_REAL_SEND=false)."
            )
            await self._audit.record(
                action="outreach_dispatch_blocked",
                result="blocked",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="outreach_dispatch",
                entity_id=dispatch.id,
                reason=dispatch.last_error,
                request=http_request,
            )
            return
        if dispatch.email_draft_id is None:
            dispatch.dispatch_status = "failed"
            dispatch.last_error = "No email draft is linked to this dispatch."
            return

        result = await provider.send_manual_confirmed_message(
            user_id=actor_user_id or dispatch.created_by_user_id,
            email_draft_id=dispatch.email_draft_id,
            dispatch_id=dispatch.id,
        )
        if result.blocked:
            dispatch.dispatch_status = "failed"
            dispatch.last_error = result.message
            await self._audit.record(
                action="outreach_dispatch_failed",
                result="failed",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="outreach_dispatch",
                entity_id=dispatch.id,
                reason=result.message,
                request=http_request,
            )
            return

        dispatch.dispatch_status = "sent_manually_confirmed"
        dispatch.provider_message_id = result.provider_message_id
        dispatch.provider_url = result.provider_url
        dispatch.last_error = None

        await self._advance_queue_item(
            dispatch, "sent_manually_confirmed", actor_user_id, actor_role, http_request
        )
        await self._audit.record(
            action=(
                "outreach_manual_send_simulated"
                if provider.name == "mock"
                else "outreach_manual_send_real_executed"
            ),
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_dispatch",
            entity_id=dispatch.id,
            metadata={"provider": provider.name},
            request=http_request,
        )

    async def _advance_queue_item(
        self,
        dispatch: OutreachDispatch,
        queue_status: str,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None,
    ) -> None:
        # Best-effort bookkeeping only: the dispatch record above is always
        # the authoritative outcome, so an unusual queue item state must
        # never crash a dispatch action that has already completed.
        try:
            await self._outreach_queue_service.update_queue_item_status(
                dispatch.queue_item_id,
                UpdateQueueItemStatusRequest(queue_status=queue_status),
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                http_request=http_request,
            )
        except (
            OutreachQueueItemNotFoundError,
            InvalidOutreachQueueStatusTransitionError,
            OutreachQueueItemBlockedError,
        ):
            pass

    # -- cancel -------------------------------------------------------------------------

    async def cancel(
        self,
        dispatch_id: UUID,
        request: CancelDispatchRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> CancelDispatchResponse:
        dispatch = await self._get_or_404(dispatch_id)
        if dispatch.dispatch_status in (
            "external_draft_created",
            "sent_manually_confirmed",
            "cancelled",
            "archived",
        ):
            raise OutreachDispatchNotReadyError(
                [f"Dispatch is already '{dispatch.dispatch_status}' and cannot be cancelled."]
            )

        dispatch.dispatch_status = "cancelled"
        dispatch.last_error = request.reason
        updated = await self._dispatches.update(dispatch)
        assert updated is not None

        await self._advance_queue_item(
            dispatch, "cancelled", actor_user_id, actor_role, http_request
        )
        await self._audit.record(
            action="outreach_dispatch_cancelled",
            result="cancelled",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_dispatch",
            entity_id=dispatch_id,
            reason=request.reason,
            request=http_request,
        )
        return CancelDispatchResponse(
            dispatch=OutreachDispatchResponse.model_validate(updated)
        )
