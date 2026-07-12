"""Outreach Campaign Queue: collects already-qualified Lead Candidates and
CRM Leads into prioritized, campaign-scoped queues for human review.

Never sends an email, never contacts anyone, and never creates an external
(Gmail/Outlook) draft by itself. Building a queue only ever scores and
sorts existing Lead Qualification results; moving a queue item forward
(workflow preparation, batch preparation) only ever prepares an internal
Sales Workflow run / internal email draft through a deliberate,
human-triggered action. Do-not-contact is re-verified at every step and can
never be bypassed; Human Review is never skipped.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Request

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.outreach.schemas import (
    BuildOutreachQueueRequest,
    BuildOutreachQueueResponse,
    CreateOutreachCampaignRequest,
    OutreachCampaignListResponse,
    OutreachCampaignResponse,
    OutreachQueueDashboardResponse,
    OutreachQueueItemListResponse,
    OutreachQueueItemResponse,
    OutreachQueueStatusResponse,
    PrepareQueueBatchRequest,
    PrepareQueueBatchResponse,
    PrepareQueueItemWorkflowRequest,
    PrepareQueueItemWorkflowResponse,
    UpdateOutreachCampaignRequest,
    UpdateQueueItemStatusRequest,
    UpdateQueueItemStatusResponse,
)
from backend.application.sales_strategy.offer_service import OfferService
from backend.application.workflows.exceptions import WorkflowStepError
from backend.application.workflows.sales_workflow import SalesWorkflowService
from backend.application.workflows.schemas import SalesWorkflowRequest
from backend.domain.entities.outreach_campaign import OutreachCampaign
from backend.domain.entities.outreach_queue_item import OutreachQueueItem
from backend.domain.entities.qualification_result import QualificationResult
from backend.domain.exceptions import (
    InvalidOutreachQueueStatusTransitionError,
    OfferProfileNotFoundError,
    OutreachCampaignNotFoundError,
    OutreachQueueItemBlockedError,
    OutreachQueueItemNotFoundError,
)
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.lead_candidate_repository import (
    LeadCandidateRepository,
)
from backend.domain.repositories.lead_repository import LeadRepository
from backend.domain.repositories.outreach_campaign_repository import (
    OutreachCampaignRepository,
)
from backend.domain.repositories.outreach_queue_item_repository import (
    OutreachQueueItemRepository,
)
from backend.domain.repositories.qualification_result_repository import (
    QualificationResultRepository,
)
from backend.shared.config import Settings

#: Cap applied when the caller asks to build/prepare "everything eligible"
#: without supplying explicit ids.
_DEFAULT_RESOLVE_LIMIT = 200

#: Terminal/settled queue statuses a rebuild must never silently overwrite.
_SETTLED_STATUSES = frozenset(
    {
        "rejected",
        "external_draft_created",
        "replied",
        "archived",
        "sent_manually_confirmed",
        "failed",
        "cancelled",
    }
)

#: Valid manual queue-status transitions. 'blocked' may only ever move to
#: 'archived' here — moving a blocked item back into the active flow
#: requires a fresh do-not-contact re-check (handled as a special case in
#: ``update_queue_item_status``, never a plain transition).
#:
#: 'sent_manually_confirmed'/'failed'/'cancelled' are set only by
#: Controlled Outreach Dispatch (see
#: ``backend.application.outreach.outreach_dispatch_service``), always
#: through this same validated method — never automatically, and never
#: for a batch of items at once.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"ready_for_workflow", "needs_review", "blocked", "archived"},
    "needs_review": {"queued", "ready_for_workflow", "blocked", "archived"},
    "ready_for_workflow": {"workflow_prepared", "blocked", "archived"},
    "workflow_prepared": {"draft_created", "blocked", "archived"},
    "draft_created": {"review_pending", "blocked", "archived"},
    "review_pending": {"approved", "rejected", "archived"},
    "approved": {
        "external_draft_created",
        "sent_manually_confirmed",
        "failed",
        "cancelled",
        "archived",
    },
    "rejected": {"archived"},
    "external_draft_created": {
        "replied",
        "sent_manually_confirmed",
        "failed",
        "cancelled",
        "archived",
    },
    "sent_manually_confirmed": {"replied", "archived"},
    "failed": {"archived"},
    "cancelled": {"archived"},
    "replied": {"archived"},
    "blocked": {"archived"},
    "archived": set(),
}

_RECHECKABLE_FROM_BLOCKED = {"queued", "ready_for_workflow", "needs_review"}


def _to_uuid(value: str | None) -> UUID | None:
    return UUID(value) if value else None


class OutreachQueueService:
    def __init__(
        self,
        campaigns: OutreachCampaignRepository,
        queue_items: OutreachQueueItemRepository,
        qualification_results: QualificationResultRepository,
        lead_candidates: LeadCandidateRepository,
        companies: CompanyRepository,
        leads: LeadRepository,
        compliance: DoNotContactService,
        offer_service: OfferService,
        sales_workflow: SalesWorkflowService,
        audit: AuditLogService,
        settings: Settings,
    ) -> None:
        self._campaigns = campaigns
        self._queue_items = queue_items
        self._qualification_results = qualification_results
        self._lead_candidates = lead_candidates
        self._companies = companies
        self._leads = leads
        self._compliance = compliance
        self._offer_service = offer_service
        self._sales_workflow = sales_workflow
        self._audit = audit
        self._settings = settings

    # -- status / dashboard ----------------------------------------------------------

    async def get_status(self) -> OutreachQueueStatusResponse:
        warnings: list[str] = []
        if not self._settings.outreach_queue_enabled:
            warnings.append("Outreach Queue is disabled (OUTREACH_QUEUE_ENABLED=false).")
        if self._settings.outreach_queue_auto_create_external_drafts:
            warnings.append(
                "OUTREACH_QUEUE_AUTO_CREATE_EXTERNAL_DRAFTS is set, but this build "
                "never creates external drafts automatically regardless of this flag."
            )
        return OutreachQueueStatusResponse(
            enabled=self._settings.outreach_queue_enabled,
            default_min_score=self._settings.outreach_queue_default_min_score,
            default_batch_size=self._settings.outreach_queue_default_batch_size,
            max_batch_size=self._settings.outreach_queue_max_batch_size,
            require_qualification=self._settings.outreach_queue_require_qualification,
            require_human_review=self._settings.outreach_queue_require_human_review,
            allow_batch_workflow_prep=self._settings.outreach_queue_allow_batch_workflow_prep,
            auto_create_external_drafts=False,
            warnings=warnings,
        )

    async def get_dashboard(self) -> OutreachQueueDashboardResponse:
        campaigns = await self._campaigns.list(limit=100)
        items = await self._queue_items.list(limit=1000)

        def _count(status: str) -> int:
            return sum(1 for i in items if i.queue_status == status)

        warnings: list[str] = []
        if not campaigns:
            warnings.append("No campaigns yet — create one to start building a queue.")

        return OutreachQueueDashboardResponse(
            total_queued=_count("queued"),
            total_blocked=_count("blocked"),
            total_needs_review=_count("needs_review"),
            total_ready_for_workflow=_count("ready_for_workflow"),
            total_workflow_prepared=_count("workflow_prepared"),
            total_draft_created=_count("draft_created"),
            total_review_pending=_count("review_pending"),
            total_approved=_count("approved"),
            total_rejected=_count("rejected"),
            total_external_draft_created=_count("external_draft_created"),
            total_archived=_count("archived"),
            campaigns=[OutreachCampaignResponse.model_validate(c) for c in campaigns],
            warnings=warnings,
        )

    # -- campaigns --------------------------------------------------------------------

    async def create_campaign(
        self,
        request: CreateOutreachCampaignRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> OutreachCampaignResponse:
        campaign = await self._campaigns.create(
            OutreachCampaign(
                name=request.name,
                description=request.description,
                icp_profile_id=request.icp_profile_id,
                offer_profile_id=request.offer_profile_id,
                target_language=request.target_language,
                tone=request.tone,
                min_qualification_score=(
                    request.min_qualification_score
                    if request.min_qualification_score is not None
                    else self._settings.outreach_queue_default_min_score
                ),
                allowed_qualification_levels=request.allowed_qualification_levels,
                excluded_statuses=request.excluded_statuses,
                max_queue_items=(
                    request.max_queue_items
                    if request.max_queue_items is not None
                    else self._settings.outreach_queue_default_batch_size
                ),
                status="draft",
                created_by_user_id=actor_user_id,
            )
        )
        await self._audit.record(
            action="outreach_campaign_created",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_campaign",
            entity_id=campaign.id,
            metadata={"name": campaign.name},
            request=http_request,
        )
        return OutreachCampaignResponse.model_validate(campaign)

    async def list_campaigns(
        self, limit: int = 100, offset: int = 0, status: str | None = None
    ) -> OutreachCampaignListResponse:
        campaigns = await self._campaigns.list(limit=limit, offset=offset, status=status)
        return OutreachCampaignListResponse(
            items=[OutreachCampaignResponse.model_validate(c) for c in campaigns],
            limit=limit,
            offset=offset,
        )

    async def get_campaign(self, campaign_id: UUID) -> OutreachCampaignResponse:
        campaign = await self._campaigns.get_by_id(campaign_id)
        if campaign is None:
            raise OutreachCampaignNotFoundError(campaign_id)
        return OutreachCampaignResponse.model_validate(campaign)

    async def update_campaign(
        self,
        campaign_id: UUID,
        request: UpdateOutreachCampaignRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> OutreachCampaignResponse:
        campaign = await self._campaigns.get_by_id(campaign_id)
        if campaign is None:
            raise OutreachCampaignNotFoundError(campaign_id)

        updates = request.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            setattr(campaign, field_name, value)

        updated = await self._campaigns.update(campaign)
        if updated is None:
            raise OutreachCampaignNotFoundError(campaign_id)
        await self._audit.record(
            action="outreach_campaign_updated",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_campaign",
            entity_id=campaign_id,
            request=http_request,
        )
        return OutreachCampaignResponse.model_validate(updated)

    async def archive_campaign(
        self,
        campaign_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> OutreachCampaignResponse:
        updated = await self._campaigns.archive(campaign_id)
        if updated is None:
            raise OutreachCampaignNotFoundError(campaign_id)
        await self._audit.record(
            action="outreach_campaign_archived",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_campaign",
            entity_id=campaign_id,
            request=http_request,
        )
        return OutreachCampaignResponse.model_validate(updated)

    async def set_campaign_status(
        self,
        campaign_id: UUID,
        status: str,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> OutreachCampaignResponse:
        campaign = await self._campaigns.get_by_id(campaign_id)
        if campaign is None:
            raise OutreachCampaignNotFoundError(campaign_id)
        # Archived is terminal from this endpoint — archive_campaign is the
        # single, explicit way in; reactivating requires a fresh campaign.
        if campaign.status == "archived":
            raise InvalidOutreachQueueStatusTransitionError(campaign.status, status)

        updated = await self._campaigns.set_status(campaign_id, status)
        if updated is None:
            raise OutreachCampaignNotFoundError(campaign_id)
        await self._audit.record(
            action="outreach_campaign_status_changed",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_campaign",
            entity_id=campaign_id,
            metadata={"status": status},
            request=http_request,
        )
        return OutreachCampaignResponse.model_validate(updated)

    # -- queue build --------------------------------------------------------------------

    async def build_queue(
        self,
        campaign_id: UUID,
        request: BuildOutreachQueueRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> BuildOutreachQueueResponse:
        campaign = await self._campaigns.get_by_id(campaign_id)
        if campaign is None:
            raise OutreachCampaignNotFoundError(campaign_id)

        min_score = (
            request.min_score if request.min_score is not None else campaign.min_qualification_score
        )
        max_items = min(
            request.max_items or campaign.max_queue_items,
            self._settings.outreach_queue_max_batch_size,
        )

        warnings: list[str] = []
        results = await self._resolve_results(
            request.qualification_result_ids, request.lead_ids, warnings
        )

        eligible: list[QualificationResult] = []
        skipped_count = 0
        for result in results:
            if result.qualification_score < min_score:
                skipped_count += 1
                warnings.append(
                    f"Qualification result {result.id} skipped: score "
                    f"{result.qualification_score} is below min_score ({min_score})."
                )
                continue
            if result.qualification_status == "disqualified":
                skipped_count += 1
                warnings.append(
                    f"Qualification result {result.id} skipped: marked disqualified"
                    + (f" ({result.disqualification_reason})." if result.disqualification_reason else ".")
                )
                continue
            if result.qualification_status == "duplicate" or result.duplicate_status == "duplicate":
                skipped_count += 1
                warnings.append(
                    f"Qualification result {result.id} skipped: marked duplicate."
                )
                continue
            if (
                campaign.allowed_qualification_levels
                and result.qualification_level not in campaign.allowed_qualification_levels
            ):
                skipped_count += 1
                warnings.append(
                    f"Qualification result {result.id} skipped: level "
                    f"'{result.qualification_level}' is not in this campaign's "
                    "allowed_qualification_levels."
                )
                continue
            if result.qualification_status in campaign.excluded_statuses:
                skipped_count += 1
                warnings.append(
                    f"Qualification result {result.id} skipped: status "
                    f"'{result.qualification_status}' is excluded for this campaign."
                )
                continue
            eligible.append(result)

        eligible.sort(key=lambda r: r.qualification_score, reverse=True)
        eligible = eligible[:max_items]

        blocked_count = 0
        response_items: list[OutreachQueueItem] = []

        for rank, result in enumerate(eligible, start=1):
            item, is_blocked = await self._build_queue_item(
                result, campaign, priority_rank=rank, actor_user_id=actor_user_id
            )
            if is_blocked:
                blocked_count += 1

            if request.dry_run:
                response_items.append(item)
                continue

            existing = await self._queue_items.find_existing_item(
                campaign_id,
                lead_id=result.lead_id,
                company_id=result.company_id if not (result.lead_id or result.lead_candidate_id) else None,
                lead_candidate_id=result.lead_candidate_id,
            )
            if existing is not None:
                if existing.queue_status in _SETTLED_STATUSES:
                    response_items.append(existing)
                    continue
                existing.priority_rank = item.priority_rank
                existing.qualification_score = item.qualification_score
                existing.qualification_level = item.qualification_level
                existing.recommended_outreach_angle = item.recommended_outreach_angle
                existing.personalization_notes = item.personalization_notes
                existing.compliance_status = item.compliance_status
                existing.do_not_contact_status = item.do_not_contact_status
                existing.duplicate_status = item.duplicate_status
                existing.queue_status = item.queue_status
                saved = await self._queue_items.update(existing)
                assert saved is not None
                response_items.append(saved)
            else:
                saved = await self._queue_items.create(item)
                response_items.append(saved)

        await self._audit.record(
            action="outreach_queue_dry_run" if request.dry_run else "outreach_queue_built",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_campaign",
            entity_id=campaign_id,
            metadata={
                "items": len(response_items),
                "skipped_count": skipped_count,
                "blocked_count": blocked_count,
                "dry_run": request.dry_run,
            },
            request=http_request,
        )
        if blocked_count > 0:
            await self._audit.record(
                action="outreach_do_not_contact_blocked",
                result="blocked",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="outreach_campaign",
                entity_id=campaign_id,
                metadata={"blocked_count": blocked_count},
                request=http_request,
            )

        return BuildOutreachQueueResponse(
            campaign=OutreachCampaignResponse.model_validate(campaign),
            items=[OutreachQueueItemResponse.model_validate(i) for i in response_items],
            skipped_count=skipped_count,
            blocked_count=blocked_count,
            dry_run=request.dry_run,
            warnings=warnings,
        )

    async def _resolve_results(
        self,
        qualification_result_ids: list[UUID],
        lead_ids: list[UUID],
        warnings: list[str],
    ) -> list[QualificationResult]:
        results: list[QualificationResult] = []
        seen_ids: set[UUID] = set()

        for result_id in qualification_result_ids:
            result = await self._qualification_results.get_by_id(result_id)
            if result is None:
                warnings.append(
                    f"Qualification result {result_id} was not found and was skipped."
                )
                continue
            if result.id not in seen_ids:
                results.append(result)
                seen_ids.add(result.id)

        for lead_id in lead_ids:
            result = await self._qualification_results.find_latest_for_lead(lead_id)
            if result is None:
                warnings.append(
                    f"Lead {lead_id} has no qualification result and was skipped "
                    "(build a Lead Qualification result for it first)."
                )
                continue
            if result.id not in seen_ids:
                results.append(result)
                seen_ids.add(result.id)

        if not qualification_result_ids and not lead_ids:
            for status in ("priority", "qualified"):
                for result in await self._qualification_results.list(
                    limit=_DEFAULT_RESOLVE_LIMIT, qualification_status=status
                ):
                    if result.id not in seen_ids:
                        results.append(result)
                        seen_ids.add(result.id)

        return results

    async def _build_queue_item(
        self,
        result: QualificationResult,
        campaign: OutreachCampaign,
        *,
        priority_rank: int,
        actor_user_id: UUID | None,
    ) -> tuple[OutreachQueueItem, bool]:
        email: str | None = None
        domain: str | None = None
        company_name: str | None = None

        if result.company_id is not None:
            company = await self._companies.get(result.company_id)
            if company is not None:
                domain = company.domain
                company_name = company.name
        if result.lead_candidate_id is not None:
            candidate = await self._lead_candidates.get_by_id(result.lead_candidate_id)
            if candidate is not None:
                email = candidate.public_contact_email
                company_name = company_name or candidate.company_name
                domain = domain or candidate.company_domain

        dnc = await self._compliance.check(email=email, domain=domain, company_name=company_name)
        is_blocked = dnc.is_blocked or result.compliance_status == "blocked"

        if is_blocked:
            queue_status = "blocked"
        elif result.qualification_status == "needs_review":
            queue_status = "needs_review"
        else:
            queue_status = "queued"

        item = OutreachQueueItem(
            campaign_id=campaign.id,
            lead_id=result.lead_id,
            company_id=result.company_id,
            lead_candidate_id=result.lead_candidate_id,
            qualification_result_id=result.id,
            icp_profile_id=result.icp_profile_id or campaign.icp_profile_id,
            offer_profile_id=result.offer_profile_id or campaign.offer_profile_id,
            priority_rank=priority_rank,
            qualification_score=result.qualification_score,
            qualification_level=result.qualification_level,
            queue_status=queue_status,
            recommended_outreach_angle=result.recommended_outreach_angle,
            personalization_notes=result.fit_summary,
            compliance_status="blocked" if is_blocked else "clear",
            do_not_contact_status="blocked" if is_blocked else "clear",
            duplicate_status=result.duplicate_status,
            created_by_user_id=actor_user_id,
        )
        return item, is_blocked

    # -- listing ----------------------------------------------------------------------

    async def list_queue_items(
        self,
        limit: int = 100,
        offset: int = 0,
        campaign_id: UUID | None = None,
        queue_status: str | None = None,
    ) -> OutreachQueueItemListResponse:
        items = await self._queue_items.list(
            limit=limit, offset=offset, campaign_id=campaign_id, queue_status=queue_status
        )
        return OutreachQueueItemListResponse(
            items=[OutreachQueueItemResponse.model_validate(i) for i in items],
            limit=limit,
            offset=offset,
        )

    async def get_queue_item(self, item_id: UUID) -> OutreachQueueItemResponse:
        item = await self._queue_items.get_by_id(item_id)
        if item is None:
            raise OutreachQueueItemNotFoundError(item_id)
        return OutreachQueueItemResponse.model_validate(item)

    # -- status update ------------------------------------------------------------------

    async def update_queue_item_status(
        self,
        item_id: UUID,
        request: UpdateQueueItemStatusRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> UpdateQueueItemStatusResponse:
        item = await self._queue_items.get_by_id(item_id)
        if item is None:
            raise OutreachQueueItemNotFoundError(item_id)

        current = item.queue_status
        target = request.queue_status

        if current != target:
            if current == "blocked" and target in _RECHECKABLE_FROM_BLOCKED:
                # Never bypass do-not-contact: re-verify before leaving
                # 'blocked', rather than trusting the old compliance_status.
                dnc = await self._recheck_compliance(item)
                if dnc.is_blocked:
                    item.last_error = "Still blocked by an active do-not-contact entry."
                    await self._queue_items.update(item)
                    raise OutreachQueueItemBlockedError(item_id)
                item.compliance_status = "clear"
                item.do_not_contact_status = "clear"
            else:
                allowed = _ALLOWED_TRANSITIONS.get(current, set())
                if target not in allowed:
                    raise InvalidOutreachQueueStatusTransitionError(current, target)

        item.queue_status = target
        item.last_action = f"status_set_to_{target}"
        if request.external_draft_id is not None:
            item.external_draft_id = request.external_draft_id
        if request.notes:
            item.personalization_notes = (
                f"{item.personalization_notes}\n\nNote: {request.notes}"
                if item.personalization_notes
                else f"Note: {request.notes}"
            )

        updated = await self._queue_items.update(item)
        assert updated is not None

        await self._audit.record(
            action="outreach_queue_item_status_changed",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_queue_item",
            entity_id=item_id,
            metadata={"from": current, "to": target},
            request=http_request,
        )
        return UpdateQueueItemStatusResponse(
            item=OutreachQueueItemResponse.model_validate(updated)
        )

    async def _recheck_compliance(self, item: OutreachQueueItem):
        email = None
        domain = None
        company_name = None
        if item.company_id is not None:
            company = await self._companies.get(item.company_id)
            if company is not None:
                domain = company.domain
                company_name = company.name
        if item.lead_candidate_id is not None:
            candidate = await self._lead_candidates.get_by_id(item.lead_candidate_id)
            if candidate is not None:
                email = candidate.public_contact_email
                company_name = company_name or candidate.company_name
                domain = domain or candidate.company_domain
        return await self._compliance.check(email=email, domain=domain, company_name=company_name)

    # -- workflow preparation ------------------------------------------------------------

    async def prepare_queue_item_workflow(
        self,
        item_id: UUID,
        request: PrepareQueueItemWorkflowRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> PrepareQueueItemWorkflowResponse:
        item = await self._queue_items.get_by_id(item_id)
        if item is None:
            raise OutreachQueueItemNotFoundError(item_id)

        if item.queue_status == "blocked":
            raise OutreachQueueItemBlockedError(item_id)
        if item.queue_status not in ("queued", "ready_for_workflow", "needs_review"):
            raise InvalidOutreachQueueStatusTransitionError(
                item.queue_status, "workflow_prepared"
            )

        response = await self._run_workflow_for_item(item, notes=request.notes)

        if response.blocked:
            item.queue_status = "blocked"
            item.compliance_status = "blocked"
            item.do_not_contact_status = "blocked"
            item.last_error = "Blocked by do-not-contact during workflow preparation."
            updated_blocked = await self._queue_items.update(item)
            await self._audit.record(
                action="outreach_do_not_contact_blocked",
                result="blocked",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="outreach_queue_item",
                entity_id=item_id,
                request=http_request,
            )
            if updated_blocked is not None:
                response.item = OutreachQueueItemResponse.model_validate(updated_blocked)
            return response

        item.workflow_run_id = _to_uuid(response.workflow_id)
        item.email_draft_id = _to_uuid(response.email_draft_id)
        item.review_id = _to_uuid(response.email_draft_id) or item.review_id
        item.queue_status = "review_pending" if response.email_draft_id else "workflow_prepared"
        item.last_action = "workflow_prepared"
        item.last_error = None
        updated = await self._queue_items.update(item)
        assert updated is not None

        await self._audit.record(
            action="outreach_queue_item_workflow_prepared",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_queue_item",
            entity_id=item_id,
            metadata={"workflow_id": response.workflow_id},
            request=http_request,
        )
        response.item = OutreachQueueItemResponse.model_validate(updated)
        return response

    async def _run_workflow_for_item(
        self, item: OutreachQueueItem, *, notes: str | None
    ) -> PrepareQueueItemWorkflowResponse:
        # Do-not-contact is re-verified here (not just trusted from
        # queue-build time) and checked *before* the Sales Workflow is even
        # started — never bypassed, and never left to the workflow's own
        # (website-url-scoped) internal check alone.
        dnc = await self._recheck_compliance(item)
        if dnc.is_blocked:
            return PrepareQueueItemWorkflowResponse(
                item=OutreachQueueItemResponse.model_validate(item),
                blocked=True,
                warnings=[
                    "Blocked by an active do-not-contact entry — the Sales "
                    "Workflow was not started."
                ],
            )

        warnings: list[str] = []
        company_name = "Unknown company"
        industry: str | None = None
        if item.company_id is not None:
            company = await self._companies.get(item.company_id)
            if company is not None:
                company_name = company.name
                industry = company.industry
        elif item.lead_candidate_id is not None:
            candidate = await self._lead_candidates.get_by_id(item.lead_candidate_id)
            if candidate is not None:
                company_name = candidate.company_name or company_name
                industry = candidate.industry

        product_or_service_offered = "unser Angebot"
        offer_profile_id = item.offer_profile_id
        if offer_profile_id is not None:
            try:
                offer = await self._offer_service.get_entity(offer_profile_id)
                product_or_service_offered = offer.main_value_proposition
            except OfferProfileNotFoundError:
                warnings.append(
                    f"Offer profile {offer_profile_id} was not found; used a "
                    "generic placeholder instead."
                )

        combined_notes_parts = [
            part
            for part in (
                item.recommended_outreach_angle,
                item.personalization_notes,
                notes,
            )
            if part
        ]
        combined_notes = "\n\n".join(combined_notes_parts) or None

        request = SalesWorkflowRequest(
            company_name=company_name,
            industry=industry,
            product_or_service_offered=product_or_service_offered,
            notes=combined_notes,
            icp_profile_id=item.icp_profile_id,
            offer_profile_id=item.offer_profile_id,
        )

        try:
            result = await self._sales_workflow.run(request)
        except WorkflowStepError as exc:
            return PrepareQueueItemWorkflowResponse(
                item=OutreachQueueItemResponse.model_validate(item),
                blocked=False,
                warnings=[*warnings, f"Sales Workflow step failed: {exc}"],
            )

        if result.status == "blocked":
            return PrepareQueueItemWorkflowResponse(
                item=OutreachQueueItemResponse.model_validate(item),
                blocked=True,
                warnings=[
                    *warnings,
                    "Blocked by an active do-not-contact entry — no draft was created.",
                ],
            )

        return PrepareQueueItemWorkflowResponse(
            item=OutreachQueueItemResponse.model_validate(item),
            workflow_id=result.workflow_id,
            email_draft_id=result.crm_email_draft_id,
            blocked=False,
            warnings=warnings,
        )

    # -- batch preparation --------------------------------------------------------------

    async def prepare_batch(
        self,
        campaign_id: UUID,
        request: PrepareQueueBatchRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> PrepareQueueBatchResponse:
        campaign = await self._campaigns.get_by_id(campaign_id)
        if campaign is None:
            raise OutreachCampaignNotFoundError(campaign_id)

        max_items = min(
            request.max_items or self._settings.outreach_queue_default_batch_size,
            self._settings.outreach_queue_max_batch_size,
        )

        if request.queue_item_ids:
            candidates: list[OutreachQueueItem] = []
            for item_id in request.queue_item_ids[:max_items]:
                item = await self._queue_items.get_by_id(item_id)
                if item is not None:
                    candidates.append(item)
        else:
            candidates = await self._queue_items.list_ready_for_workflow(
                campaign_id, limit=max_items
            )

        await self._audit.record(
            action="outreach_batch_preparation_started",
            result="started",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_campaign",
            entity_id=campaign_id,
            metadata={"total_requested": len(candidates)},
            request=http_request,
        )

        prepared_count = 0
        skipped_count = 0
        blocked_count = 0
        failed_count = 0
        warnings: list[str] = []
        result_items: list[OutreachQueueItemResponse] = []

        for item in candidates:
            if item.queue_status not in ("queued", "ready_for_workflow"):
                skipped_count += 1
                continue
            try:
                response = await self._run_workflow_for_item(item, notes=None)
            except Exception as exc:  # noqa: BLE001 - one failed item must not crash the batch
                failed_count += 1
                item.last_error = str(exc)[:300]
                updated = await self._queue_items.update(item)
                warnings.append(f"Queue item {item.id} failed: {exc}")
                if updated is not None:
                    result_items.append(OutreachQueueItemResponse.model_validate(updated))
                continue

            if response.blocked:
                blocked_count += 1
                item.queue_status = "blocked"
                item.compliance_status = "blocked"
                item.do_not_contact_status = "blocked"
                item.last_error = "Blocked by do-not-contact during batch preparation."
                updated = await self._queue_items.update(item)
                if updated is not None:
                    result_items.append(OutreachQueueItemResponse.model_validate(updated))
                continue

            item.workflow_run_id = _to_uuid(response.workflow_id)
            item.email_draft_id = _to_uuid(response.email_draft_id)
            item.review_id = _to_uuid(response.email_draft_id) or item.review_id
            item.queue_status = "review_pending" if response.email_draft_id else "workflow_prepared"
            item.last_action = "workflow_prepared"
            item.last_error = None
            updated = await self._queue_items.update(item)
            prepared_count += 1
            warnings.extend(response.warnings)
            if updated is not None:
                result_items.append(OutreachQueueItemResponse.model_validate(updated))

        await self._audit.record(
            action="outreach_batch_preparation_completed"
            if failed_count == 0
            else "outreach_batch_preparation_partially_failed",
            result="success" if failed_count == 0 else "partial_failure",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="outreach_campaign",
            entity_id=campaign_id,
            metadata={
                "prepared_count": prepared_count,
                "skipped_count": skipped_count,
                "blocked_count": blocked_count,
                "failed_count": failed_count,
            },
            request=http_request,
        )

        return PrepareQueueBatchResponse(
            total_requested=len(candidates),
            prepared_count=prepared_count,
            skipped_count=skipped_count,
            blocked_count=blocked_count,
            failed_count=failed_count,
            items=result_items,
            warnings=warnings,
        )
