"""Lead Discovery Service ("Lead Finder"): a thin, guided orchestrator over
the existing Lead Sourcing, Lead Qualification, and Outreach Queue
services. Given a target customer, region, and offer, it finds candidate
companies, has them analyzed (website research + a deterministic website
quality heuristic + ICP/Offer fit scoring), and — only via a separate,
explicit follow-up action — prepares (never sends) email drafts for the
qualified ones.

Nothing here sends an email, contacts anyone, or bypasses Do-not-contact
or Human Review — every safety gate already enforced by the services this
wraps still applies unchanged.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.lead_discovery.schemas import (
    AddCandidateToQueueResponse,
    CreateLeadDiscoveryRunRequest,
    LeadDiscoveryCandidateSummary,
    LeadDiscoveryRunDetailResponse,
    LeadDiscoveryRunListResponse,
    LeadDiscoveryRunResponse,
)
from backend.application.lead_qualification.lead_qualification_service import (
    LeadQualificationService,
)
from backend.application.lead_qualification.schemas import QualifyLeadCandidateRequest
from backend.application.lead_sourcing.lead_sourcing_service import LeadSourcingService
from backend.application.lead_sourcing.schemas import (
    CreateLeadSourcingCampaignRequest,
    StartLeadSourcingRunRequest,
)
from backend.application.outreach.outreach_queue_service import OutreachQueueService
from backend.application.outreach.schemas import (
    BuildOutreachQueueRequest,
    CreateOutreachCampaignRequest,
    PrepareQueueBatchRequest,
)
from backend.application.sales_strategy.icp_service import ICPService
from backend.application.sales_strategy.offer_service import OfferService
from backend.domain.entities.lead_discovery_run import LeadDiscoveryRun
from backend.domain.exceptions import (
    InvalidLeadDiscoveryRunTransitionError,
    LeadDiscoveryModeNotAllowedError,
    LeadDiscoveryRunNotFoundError,
)
from backend.domain.repositories.lead_candidate_repository import (
    LeadCandidateRepository,
)
from backend.domain.repositories.lead_discovery_run_repository import (
    LeadDiscoveryRunRepository,
)
from backend.domain.repositories.outreach_queue_item_repository import (
    OutreachQueueItemRepository,
)
from backend.domain.repositories.qualification_result_repository import (
    QualificationResultRepository,
)
from backend.shared.config import Settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


class LeadDiscoveryService:
    def __init__(
        self,
        runs: LeadDiscoveryRunRepository,
        candidates: LeadCandidateRepository,
        qualification_results: QualificationResultRepository,
        queue_items: OutreachQueueItemRepository,
        lead_sourcing: LeadSourcingService,
        lead_qualification: LeadQualificationService,
        outreach_queue: OutreachQueueService,
        offer_service: OfferService,
        icp_service: ICPService,
        audit: AuditLogService,
        settings: Settings,
    ) -> None:
        self._runs = runs
        self._candidates = candidates
        self._qualification_results = qualification_results
        self._queue_items = queue_items
        self._lead_sourcing = lead_sourcing
        self._lead_qualification = lead_qualification
        self._outreach_queue = outreach_queue
        self._offer_service = offer_service
        self._icp_service = icp_service
        self._audit = audit
        self._settings = settings

    # -- create -----------------------------------------------------------------------

    async def create_run(
        self,
        request: CreateLeadDiscoveryRunRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> LeadDiscoveryRunResponse:
        if request.mode == "real_llm" and not self._settings.llm_enable_real_calls:
            raise LeadDiscoveryModeNotAllowedError()

        # Fail fast with a clear error rather than deep inside the pipeline.
        await self._offer_service.get_entity(request.offer_profile_id)
        if request.icp_profile_id is not None:
            await self._icp_service.get(request.icp_profile_id)

        name = request.name or (
            f"Lead Finder: {request.target_customer}"
            + (f" ({request.region})" if request.region else "")
        )

        sourcing_campaign = await self._lead_sourcing.create_campaign(
            CreateLeadSourcingCampaignRequest(
                name=f"{name} — Sourcing"[:200],
                icp_profile_id=request.icp_profile_id,
                offer_profile_id=request.offer_profile_id,
                target_industry=request.target_customer,
                target_location=request.region,
                max_results=request.requested_count,
            ),
            created_by_user_id=actor_user_id,
        )

        outreach_campaign = await self._outreach_queue.create_campaign(
            CreateOutreachCampaignRequest(
                name=f"{name} — Review Queue"[:200],
                icp_profile_id=request.icp_profile_id,
                offer_profile_id=request.offer_profile_id,
                min_qualification_score=request.min_score,
                max_queue_items=request.requested_count,
            ),
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            http_request=http_request,
        )

        run = await self._runs.create(
            LeadDiscoveryRun(
                name=name,
                target_customer=request.target_customer,
                region=request.region,
                offer_profile_id=request.offer_profile_id,
                icp_profile_id=request.icp_profile_id,
                requested_count=request.requested_count,
                min_score=request.min_score,
                mode=request.mode,
                status="pending",
                lead_sourcing_campaign_id=sourcing_campaign.id,
                outreach_campaign_id=outreach_campaign.id,
                created_by_user_id=actor_user_id,
            )
        )
        await self._audit.record(
            action="lead_discovery_run_created",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="lead_discovery_run",
            entity_id=run.id,
            metadata={
                "target_customer": request.target_customer,
                "region": request.region,
                "mode": request.mode,
                "requested_count": request.requested_count,
            },
            request=http_request,
        )
        return LeadDiscoveryRunResponse.model_validate(run)

    # -- list / get ---------------------------------------------------------------

    async def list_runs(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        created_by_user_id: UUID | None = None,
    ) -> LeadDiscoveryRunListResponse:
        runs = await self._runs.list(
            limit=limit,
            offset=offset,
            status=status,
            created_by_user_id=created_by_user_id,
        )
        return LeadDiscoveryRunListResponse(
            items=[LeadDiscoveryRunResponse.model_validate(r) for r in runs],
            limit=limit,
            offset=offset,
        )

    async def get_run(self, run_id: UUID) -> LeadDiscoveryRunDetailResponse:
        run = await self._get_run_or_404(run_id)
        return await self._build_detail(run)

    # -- pipeline: find + analyze + qualify + queue --------------------------------

    async def run_pipeline(
        self,
        run_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> LeadDiscoveryRunDetailResponse:
        run = await self._get_run_or_404(run_id)
        if run.status == "running":
            raise InvalidLeadDiscoveryRunTransitionError(
                f"Lead Discovery Run '{run_id}' is already running."
            )
        if run.status == "completed":
            raise InvalidLeadDiscoveryRunTransitionError(
                f"Lead Discovery Run '{run_id}' has already completed — "
                "create a new run to search again."
            )

        run.status = "running"
        run.started_at = _now()
        updated = await self._runs.update(run)
        assert updated is not None
        run = updated

        try:
            sourcing_response = await self._lead_sourcing.start_run(
                StartLeadSourcingRunRequest(
                    campaign_id=run.lead_sourcing_campaign_id,
                    max_results=run.requested_count,
                ),
                started_by_user_id=actor_user_id,
                started_by_role=actor_role,
                http_request=http_request,
            )
        except Exception as exc:  # noqa: BLE001 - a failed sourcing step must be recorded, not crash the request
            run.status = "failed"
            run.completed_at = _now()
            run.errors = _dedupe([*run.errors, f"Lead sourcing failed: {exc}"])
            updated = await self._runs.update(run)
            assert updated is not None
            await self._audit.record(
                action="lead_discovery_pipeline_failed",
                result="failed",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="lead_discovery_run",
                entity_id=run.id,
                reason=str(exc),
                request=http_request,
            )
            return await self._build_detail(updated)

        run.lead_sourcing_run_id = sourcing_response.run.id
        run.found_candidates = len(sourcing_response.candidates)
        run.analyzed_websites = sum(
            1
            for candidate in sourcing_response.candidates
            if candidate.website_quality_level is not None
        )
        warnings = list(sourcing_response.run.warnings)
        errors: list[str] = []

        qualified_result_ids: list[UUID] = []
        for candidate in sourcing_response.candidates:
            if candidate.id is None:
                continue
            if candidate.do_not_contact_status == "blocked":
                run.rejected_leads += 1
                continue
            try:
                result = await self._lead_qualification.qualify_lead_candidate(
                    candidate.id,
                    QualifyLeadCandidateRequest(
                        icp_profile_id=run.icp_profile_id,
                        offer_profile_id=run.offer_profile_id,
                    ),
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    http_request=http_request,
                )
            except Exception as exc:  # noqa: BLE001 - one candidate's failure must not abort the whole run
                run.rejected_leads += 1
                errors.append(f"Qualification failed for candidate {candidate.id}: {exc}")
                continue

            if (
                result.qualification_status in ("qualified", "priority")
                and result.qualification_score >= run.min_score
            ):
                run.qualified_leads += 1
                qualified_result_ids.append(result.id)
            else:
                run.rejected_leads += 1

        if qualified_result_ids and run.outreach_campaign_id is not None:
            try:
                queue_response = await self._outreach_queue.build_queue(
                    run.outreach_campaign_id,
                    BuildOutreachQueueRequest(
                        qualification_result_ids=qualified_result_ids,
                        min_score=run.min_score,
                        max_items=run.requested_count,
                    ),
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    http_request=http_request,
                )
                warnings.extend(queue_response.warnings)
            except Exception as exc:  # noqa: BLE001 - queueing must not fail the whole pipeline result
                errors.append(f"Adding qualified leads to the review queue failed: {exc}")

        run.status = "completed"
        run.completed_at = _now()
        run.warnings = _dedupe([*run.warnings, *warnings])
        run.errors = _dedupe([*run.errors, *errors])
        updated = await self._runs.update(run)
        assert updated is not None
        run = updated

        await self._audit.record(
            action="lead_discovery_pipeline_completed",
            result="success" if not errors else "partial_failure",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="lead_discovery_run",
            entity_id=run.id,
            metadata={
                "found_candidates": run.found_candidates,
                "analyzed_websites": run.analyzed_websites,
                "qualified_leads": run.qualified_leads,
                "rejected_leads": run.rejected_leads,
            },
            request=http_request,
        )
        return await self._build_detail(run)

    # -- draft creation (separate, explicit action) --------------------------------

    async def create_drafts_for_qualified_candidates(
        self,
        run_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> LeadDiscoveryRunDetailResponse:
        run = await self._get_run_or_404(run_id)
        if run.status != "completed":
            raise InvalidLeadDiscoveryRunTransitionError(
                f"Lead Discovery Run '{run_id}' must finish its pipeline "
                f"(status='completed') before drafts can be prepared — "
                f"current status is '{run.status}'."
            )
        if run.outreach_campaign_id is None:
            return await self._build_detail(run)

        response = await self._outreach_queue.prepare_batch(
            run.outreach_campaign_id,
            PrepareQueueBatchRequest(max_items=run.requested_count),
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            http_request=http_request,
        )

        queue_items = await self._queue_items.list_by_campaign(
            run.outreach_campaign_id, limit=500
        )
        run.created_drafts = sum(
            1 for item in queue_items if item.email_draft_id is not None
        )
        run.warnings = _dedupe([*run.warnings, *response.warnings])
        updated = await self._runs.update(run)
        assert updated is not None
        run = updated

        await self._audit.record(
            action="lead_discovery_drafts_created",
            result="success" if response.failed_count == 0 else "partial_failure",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="lead_discovery_run",
            entity_id=run.id,
            metadata={
                "prepared_count": response.prepared_count,
                "failed_count": response.failed_count,
                "blocked_count": response.blocked_count,
            },
            request=http_request,
        )
        return await self._build_detail(run)

    # -- manual per-candidate queue override ----------------------------------------

    async def add_candidate_to_queue(
        self,
        run_id: UUID,
        candidate_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> AddCandidateToQueueResponse:
        """Manually queue one specific candidate for review, regardless of
        whether it crossed the run's automatic min_score threshold during
        the pipeline — a human override, never a bypass of Do-not-contact
        or duplicate checks, which ``build_queue`` still enforces."""
        run = await self._get_run_or_404(run_id)
        if run.outreach_campaign_id is None:
            return AddCandidateToQueueResponse(
                run=await self._build_detail(run),
                added=False,
                warnings=["This run has no review queue to add candidates to."],
            )

        result = await self._qualification_results.find_latest_for_candidate(candidate_id)
        if result is None:
            return AddCandidateToQueueResponse(
                run=await self._build_detail(run),
                added=False,
                warnings=["This candidate has not been qualified yet."],
            )

        response = await self._outreach_queue.build_queue(
            run.outreach_campaign_id,
            BuildOutreachQueueRequest(
                qualification_result_ids=[result.id], min_score=0, max_items=1
            ),
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            http_request=http_request,
        )
        added = len(response.items) > 0 and response.blocked_count == 0
        return AddCandidateToQueueResponse(
            run=await self._build_detail(run), added=added, warnings=response.warnings
        )

    # -- internals ------------------------------------------------------------------

    async def _get_run_or_404(self, run_id: UUID) -> LeadDiscoveryRun:
        run = await self._runs.get_by_id(run_id)
        if run is None:
            raise LeadDiscoveryRunNotFoundError(run_id)
        return run

    async def _build_detail(self, run: LeadDiscoveryRun) -> LeadDiscoveryRunDetailResponse:
        candidate_summaries: list[LeadDiscoveryCandidateSummary] = []
        if run.lead_sourcing_run_id is not None:
            raw_candidates = await self._candidates.list(
                sourcing_run_id=run.lead_sourcing_run_id, limit=500
            )
            for candidate in raw_candidates:
                if candidate.id is None:
                    continue
                result = await self._qualification_results.find_latest_for_candidate(
                    candidate.id
                )
                queue_item = None
                if run.outreach_campaign_id is not None:
                    queue_item = await self._queue_items.find_existing_item(
                        run.outreach_campaign_id,
                        lead_id=None,
                        company_id=None,
                        lead_candidate_id=candidate.id,
                    )

                draft_status: str = "none"
                email_draft_id: UUID | None = None
                if queue_item is not None and queue_item.email_draft_id is not None:
                    draft_status = "review_pending"
                    email_draft_id = queue_item.email_draft_id
                elif queue_item is not None and queue_item.workflow_run_id is not None:
                    draft_status = "prepared"

                candidate_summaries.append(
                    LeadDiscoveryCandidateSummary(
                        candidate_id=candidate.id,
                        company_name=candidate.company_name,
                        company_domain=candidate.company_domain,
                        company_website_url=candidate.company_website_url,
                        industry=candidate.industry,
                        location=candidate.location,
                        website_quality_level=candidate.website_quality_level,
                        website_quality_reasons=candidate.website_quality_reasons,
                        icp_fit_score=candidate.icp_fit_score,
                        icp_fit_level=candidate.icp_fit_level,
                        qualification_score=result.qualification_score if result else None,
                        qualification_level=result.qualification_level if result else None,
                        qualification_status=(
                            result.qualification_status if result else None
                        ),
                        fit_summary=result.fit_summary if result else None,
                        positive_signals=result.positive_signals if result else [],
                        negative_signals=result.negative_signals if result else [],
                        do_not_contact_status=candidate.do_not_contact_status,
                        duplicate_status=candidate.duplicate_status,
                        review_status=candidate.review_status,
                        in_outreach_queue=queue_item is not None,
                        draft_status=draft_status,
                        email_draft_id=email_draft_id,
                        warnings=candidate.warnings,
                    )
                )

        base = LeadDiscoveryRunResponse.model_validate(run)
        return LeadDiscoveryRunDetailResponse(
            **base.model_dump(), candidates=candidate_summaries
        )
