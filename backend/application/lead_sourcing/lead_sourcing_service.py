"""Lead Sourcing Service: finds, scores, and stages candidates for review.

Orchestrates a configured :class:`LeadSourcingProvider` together with the
existing Website Research, Do-not-contact, and ICP services. Nothing here
ever sends an email, contacts anyone, starts a Sales Workflow, or creates
an external draft. A candidate only ever becomes a CRM Company/Lead
through an explicit human :meth:`approve_candidate` call — never
automatically, regardless of configuration, because do-not-contact and
human review can never be bypassed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.lead_sourcing.schemas import (
    ApproveLeadCandidateRequest,
    ApproveLeadCandidateResponse,
    CreateLeadSourcingCampaignRequest,
    ImportLeadCandidatesRequest,
    ImportLeadCandidatesResponse,
    LeadCandidateListResponse,
    LeadCandidateResponse,
    LeadSourcingCampaignListResponse,
    LeadSourcingCampaignResponse,
    LeadSourcingProviderStatusResponse,
    LeadSourcingRunListResponse,
    LeadSourcingRunResponse,
    RejectLeadCandidateRequest,
    RejectLeadCandidateResponse,
    StartLeadSourcingRunRequest,
    StartLeadSourcingRunResponse,
    UpdateLeadSourcingCampaignRequest,
)
from backend.application.research.exceptions import (
    InvalidWebsiteURLError,
    WebsiteFetchFailedError,
)
from backend.application.research.schemas import (
    WebsiteResearchRequest,
    WebsiteResearchResponse,
)
from backend.application.research.website_research_service import (
    WebsiteResearchService,
)
from backend.application.sales_strategy.icp_service import ICPService
from backend.application.sales_strategy.schemas import ICPFitCheckRequest
from backend.domain.entities.company import Company
from backend.domain.entities.lead import Lead
from backend.domain.entities.lead_candidate import LeadCandidate
from backend.domain.entities.lead_sourcing_campaign import LeadSourcingCampaign
from backend.domain.entities.lead_sourcing_run import LeadSourcingRun
from backend.domain.enums import LeadSource
from backend.domain.exceptions import (
    LeadCandidateBlockedError,
    LeadCandidateNotFoundError,
    LeadSourcingCampaignNotFoundError,
    LeadSourcingProviderNotConfiguredError,
    LeadSourcingRunNotFoundError,
)
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.lead_candidate_repository import (
    LeadCandidateRepository,
)
from backend.domain.repositories.lead_repository import LeadRepository
from backend.domain.repositories.lead_sourcing_campaign_repository import (
    LeadSourcingCampaignRepository,
)
from backend.domain.repositories.lead_sourcing_run_repository import (
    LeadSourcingRunRepository,
)
from backend.infrastructure.lead_sourcing.base import (
    LeadSourcingProvider,
    LeadSourcingSearchQuery,
    RawLeadCandidate,
)
from backend.infrastructure.lead_sourcing.factory import get_lead_sourcing_provider
from backend.infrastructure.lead_sourcing.manual_provider import (
    ManualLeadSourcingProvider,
)
from backend.shared.config import Settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def assess_website_quality(
    research: WebsiteResearchResponse | None, research_warnings: list[str]
) -> tuple[str | None, list[str]]:
    """Deterministic, LLM-free heuristic over a website research result that
    was already fetched for ICP scoring — never a second fetch, never an
    extra LLM call, so this runs identically in Safe/Mock mode.

    Returns ``(level, reasons)`` where ``level`` is ``"poor"``, ``"medium"``,
    ``"good"``, ``"unknown"`` (a website URL was known but could not be
    fetched/analyzed), or ``None`` (no website URL was known at all, so no
    assessment was attempted).
    """
    if research is None:
        if research_warnings:
            return "unknown", ["Website konnte nicht abgerufen oder analysiert werden."]
        return None, []

    reasons: list[str] = []
    signal_score = 0
    if research.title:
        signal_score += 1
    else:
        reasons.append("Kein Seitentitel gefunden.")
    if research.meta_description:
        signal_score += 1
    else:
        reasons.append("Keine Meta-Beschreibung gefunden.")
    if research.text_length >= 500:
        signal_score += 1
    elif research.text_length < 150:
        reasons.append("Sehr wenig Textinhalt auf der Seite gefunden.")
    if research.pages_fetched > 1:
        signal_score += 1
    if research_warnings:
        reasons.append(
            f"{len(research_warnings)} Warnung(en) beim Website Research."
        )

    if signal_score >= 3:
        level = "good"
        if not reasons:
            reasons.append(
                "Titel, Meta-Beschreibung und ausreichend Textinhalt vorhanden."
            )
    elif signal_score >= 1:
        level = "medium"
    else:
        level = "poor"
        reasons.append("Kaum verwertbare Informationen auf der Website gefunden.")
    return level, reasons


class LeadSourcingService:
    def __init__(
        self,
        campaigns: LeadSourcingCampaignRepository,
        runs: LeadSourcingRunRepository,
        candidates: LeadCandidateRepository,
        companies: CompanyRepository,
        leads: LeadRepository,
        compliance: DoNotContactService,
        icp_service: ICPService,
        website_research: WebsiteResearchService,
        audit: AuditLogService,
        settings: Settings,
    ) -> None:
        self._campaigns = campaigns
        self._runs = runs
        self._candidates = candidates
        self._companies = companies
        self._leads = leads
        self._compliance = compliance
        self._icp_service = icp_service
        self._website_research = website_research
        self._audit = audit
        self._settings = settings

    # -- provider status ----------------------------------------------------------

    async def get_provider_status(self) -> LeadSourcingProviderStatusResponse:
        provider = get_lead_sourcing_provider(self._settings)
        status = await provider.get_provider_status()
        return LeadSourcingProviderStatusResponse(
            provider=status.provider,
            real_search_enabled=status.real_search_enabled,
            status=status.status,
            max_results_per_run=self._settings.lead_sourcing_max_results_per_run,
            max_website_pages_per_company=(
                self._settings.lead_sourcing_max_website_pages_per_company
            ),
            allow_public_website_email_extraction=(
                self._settings.lead_sourcing_allow_public_website_email_extraction
            ),
            allow_personal_emails=self._settings.lead_sourcing_allow_personal_emails,
            require_review_before_crm=(
                self._settings.lead_sourcing_require_review_before_crm
            ),
            warnings=status.warnings,
        )

    # -- campaigns ------------------------------------------------------------------

    async def create_campaign(
        self, request: CreateLeadSourcingCampaignRequest, created_by_user_id: UUID | None
    ) -> LeadSourcingCampaignResponse:
        max_results = min(request.max_results, self._settings.lead_sourcing_max_results_per_run)
        campaign = LeadSourcingCampaign(
            name=request.name,
            description=request.description,
            icp_profile_id=request.icp_profile_id,
            offer_profile_id=request.offer_profile_id,
            source_type=self._settings.lead_sourcing_provider,
            search_query=request.search_query,
            target_industry=request.target_industry,
            target_location=request.target_location,
            target_keywords=request.target_keywords,
            excluded_keywords=request.excluded_keywords,
            max_results=max_results,
            status="draft",
            created_by_user_id=created_by_user_id,
        )
        created = await self._campaigns.create(campaign)
        return LeadSourcingCampaignResponse.model_validate(created)

    async def list_campaigns(
        self, limit: int = 100, offset: int = 0, status: str | None = None
    ) -> LeadSourcingCampaignListResponse:
        campaigns = await self._campaigns.list(limit=limit, offset=offset, status=status)
        return LeadSourcingCampaignListResponse(
            items=[LeadSourcingCampaignResponse.model_validate(c) for c in campaigns],
            limit=limit,
            offset=offset,
        )

    async def get_campaign(self, campaign_id: UUID) -> LeadSourcingCampaignResponse:
        campaign = await self._campaigns.get_by_id(campaign_id)
        if campaign is None:
            raise LeadSourcingCampaignNotFoundError(campaign_id)
        return LeadSourcingCampaignResponse.model_validate(campaign)

    async def update_campaign(
        self, campaign_id: UUID, request: UpdateLeadSourcingCampaignRequest
    ) -> LeadSourcingCampaignResponse:
        existing = await self._campaigns.get_by_id(campaign_id)
        if existing is None:
            raise LeadSourcingCampaignNotFoundError(campaign_id)

        updates = request.model_dump(exclude_unset=True)
        if "max_results" in updates and updates["max_results"] is not None:
            updates["max_results"] = min(
                updates["max_results"], self._settings.lead_sourcing_max_results_per_run
            )
        for field_name, value in updates.items():
            setattr(existing, field_name, value)

        updated = await self._campaigns.update(existing)
        if updated is None:
            raise LeadSourcingCampaignNotFoundError(campaign_id)
        return LeadSourcingCampaignResponse.model_validate(updated)

    async def archive_campaign(self, campaign_id: UUID) -> LeadSourcingCampaignResponse:
        updated = await self._campaigns.archive(campaign_id)
        if updated is None:
            raise LeadSourcingCampaignNotFoundError(campaign_id)
        return LeadSourcingCampaignResponse.model_validate(updated)

    # -- runs / candidates listing --------------------------------------------------

    async def list_runs(
        self, limit: int = 100, offset: int = 0, campaign_id: UUID | None = None
    ) -> LeadSourcingRunListResponse:
        runs = await self._runs.list(limit=limit, offset=offset, campaign_id=campaign_id)
        return LeadSourcingRunListResponse(
            items=[LeadSourcingRunResponse.model_validate(r) for r in runs],
            limit=limit,
            offset=offset,
        )

    async def get_run(self, run_id: UUID) -> LeadSourcingRunResponse:
        run = await self._runs.get_by_id(run_id)
        if run is None:
            raise LeadSourcingRunNotFoundError(run_id)
        return LeadSourcingRunResponse.model_validate(run)

    async def list_candidates(
        self,
        limit: int = 100,
        offset: int = 0,
        campaign_id: UUID | None = None,
        sourcing_run_id: UUID | None = None,
        review_status: str | None = None,
    ) -> LeadCandidateListResponse:
        candidates = await self._candidates.list(
            limit=limit,
            offset=offset,
            campaign_id=campaign_id,
            sourcing_run_id=sourcing_run_id,
            review_status=review_status,
        )
        return LeadCandidateListResponse(
            items=[LeadCandidateResponse.model_validate(c) for c in candidates],
            limit=limit,
            offset=offset,
        )

    async def get_candidate(self, candidate_id: UUID) -> LeadCandidateResponse:
        candidate = await self._candidates.get_by_id(candidate_id)
        if candidate is None:
            raise LeadCandidateNotFoundError(candidate_id)
        return LeadCandidateResponse.model_validate(candidate)

    # -- run start / dry run ---------------------------------------------------------

    async def start_run(
        self,
        request: StartLeadSourcingRunRequest,
        started_by_user_id: UUID | None,
        started_by_role: str | None,
        http_request: Request | None = None,
    ) -> StartLeadSourcingRunResponse:
        campaign = await self._campaigns.get_by_id(request.campaign_id)
        if campaign is None:
            raise LeadSourcingCampaignNotFoundError(request.campaign_id)

        provider = get_lead_sourcing_provider(self._settings)
        max_results = min(
            request.max_results or campaign.max_results,
            self._settings.lead_sourcing_max_results_per_run,
        )

        run = await self._runs.create(
            LeadSourcingRun(
                campaign_id=campaign.id,
                status="running",
                provider=provider.name,
                started_by_user_id=started_by_user_id,
                started_at=_now(),
            )
        )
        await self._audit.record(
            action="lead_sourcing_run_started",
            result="started",
            actor_user_id=started_by_user_id,
            actor_role=started_by_role,
            entity_type="lead_sourcing_run",
            entity_id=run.id,
            metadata={"campaign_id": str(campaign.id), "dry_run": request.dry_run},
            request=http_request,
        )
        if not request.dry_run:
            campaign.status = "running"
            await self._campaigns.update(campaign)

        try:
            raw_candidates = await provider.search_companies(
                LeadSourcingSearchQuery(
                    search_query=campaign.search_query,
                    target_industry=campaign.target_industry,
                    target_location=campaign.target_location,
                    target_keywords=campaign.target_keywords,
                    excluded_keywords=campaign.excluded_keywords,
                    max_results=max_results,
                )
            )
        except LeadSourcingProviderNotConfiguredError as exc:
            run.status = "failed"
            run.completed_at = _now()
            run.warnings = [str(exc)]
            await self._runs.update(run)
            if not request.dry_run:
                campaign.status = "failed"
                await self._campaigns.update(campaign)
            await self._audit.record(
                action="lead_sourcing_run_failed",
                result="failed",
                actor_user_id=started_by_user_id,
                actor_role=started_by_role,
                entity_type="lead_sourcing_run",
                entity_id=run.id,
                reason=str(exc),
                request=http_request,
            )
            raise

        candidate_responses: list[LeadCandidateResponse] = []
        for raw in raw_candidates:
            candidate = await self._process_candidate(
                raw,
                campaign=campaign,
                run=run,
                provider=provider,
                extra_notes=[],
                persist=not request.dry_run,
                actor_user_id=started_by_user_id,
                actor_role=started_by_role,
                http_request=http_request,
            )
            candidate_responses.append(LeadCandidateResponse.model_validate(candidate))

        run.status = "completed"
        run.completed_at = _now()
        updated_run = await self._runs.update(run)
        assert updated_run is not None

        if not request.dry_run:
            campaign.status = "completed"
            await self._campaigns.update(campaign)

        await self._audit.record(
            action="lead_sourcing_run_completed",
            result="success",
            actor_user_id=started_by_user_id,
            actor_role=started_by_role,
            entity_type="lead_sourcing_run",
            entity_id=run.id,
            metadata={
                "total_candidates_found": updated_run.total_candidates_found,
                "total_candidates_saved": updated_run.total_candidates_saved,
                "dry_run": request.dry_run,
            },
            request=http_request,
        )

        return StartLeadSourcingRunResponse(
            run=LeadSourcingRunResponse.model_validate(updated_run),
            candidates=candidate_responses,
            dry_run=request.dry_run,
        )

    # -- manual import ------------------------------------------------------------

    async def import_candidates(
        self,
        request: ImportLeadCandidatesRequest,
        imported_by_user_id: UUID | None,
        imported_by_role: str | None,
        http_request: Request | None = None,
    ) -> ImportLeadCandidatesResponse:
        campaign = await self._campaigns.get_by_id(request.campaign_id)
        if campaign is None:
            raise LeadSourcingCampaignNotFoundError(request.campaign_id)

        # Manual import is always attributed to the manual provider,
        # regardless of the configured search provider — it is user-entered
        # text, never a search.
        provider = ManualLeadSourcingProvider()
        run = await self._runs.create(
            LeadSourcingRun(
                campaign_id=campaign.id,
                status="running",
                provider="manual",
                started_by_user_id=imported_by_user_id,
                started_at=_now(),
            )
        )

        warnings: list[str] = []
        candidate_responses: list[LeadCandidateResponse] = []
        for raw_line in request.raw_text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            company_name = parts[0] if len(parts) > 0 and parts[0] else None
            domain = parts[1] if len(parts) > 1 and parts[1] else None
            website_url = parts[2] if len(parts) > 2 and parts[2] else None
            note = parts[3] if len(parts) > 3 and parts[3] else None

            if not company_name and not domain:
                warnings.append(f"Skipped line (no company_name or domain): '{line}'")
                run.total_errors += 1
                continue

            raw_candidate = RawLeadCandidate(
                company_name=company_name,
                company_domain=domain,
                company_website_url=website_url,
                source_name="manual-import",
            )
            candidate = await self._process_candidate(
                raw_candidate,
                campaign=campaign,
                run=run,
                provider=provider,
                extra_notes=[note] if note else [],
                persist=True,
                actor_user_id=imported_by_user_id,
                actor_role=imported_by_role,
                http_request=http_request,
            )
            candidate_responses.append(LeadCandidateResponse.model_validate(candidate))

        run.status = "completed"
        run.completed_at = _now()
        run.warnings = warnings
        updated_run = await self._runs.update(run)
        assert updated_run is not None

        await self._audit.record(
            action="lead_candidate_imported",
            result="success",
            actor_user_id=imported_by_user_id,
            actor_role=imported_by_role,
            entity_type="lead_sourcing_run",
            entity_id=run.id,
            metadata={
                "campaign_id": str(campaign.id),
                "total_imported": updated_run.total_candidates_saved,
            },
            request=http_request,
        )

        return ImportLeadCandidatesResponse(
            run=LeadSourcingRunResponse.model_validate(updated_run),
            candidates=candidate_responses,
            total_imported=updated_run.total_candidates_saved,
            total_duplicates=updated_run.total_duplicates,
            total_blocked_by_do_not_contact=updated_run.total_blocked_by_do_not_contact,
            warnings=warnings,
        )

    # -- candidate processing (shared by start_run and import_candidates) ------------

    async def _process_candidate(
        self,
        raw: RawLeadCandidate,
        *,
        campaign: LeadSourcingCampaign,
        run: LeadSourcingRun,
        provider: LeadSourcingProvider,
        extra_notes: list[str],
        persist: bool,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None,
    ) -> LeadCandidate:
        normalized = provider.normalize_candidate(raw)
        enriched = await provider.enrich_company_candidate(normalized)

        notes = list(extra_notes)
        warnings: list[str] = []

        extracted_text: str | None = None
        contact_page_url: str | None = None
        website_quality_level: str | None = None
        website_quality_reasons: list[str] = []
        if enriched.company_website_url:
            research_result: WebsiteResearchResponse | None = None
            research_warnings: list[str] = []
            try:
                research_result = await self._website_research.research(
                    WebsiteResearchRequest(
                        url=enriched.company_website_url,
                        max_pages=self._settings.lead_sourcing_max_website_pages_per_company,
                        include_same_domain_links=False,
                    )
                )
            except InvalidWebsiteURLError as exc:
                message = f"Website could not be researched: {exc}"
                warnings.append(message)
                research_warnings.append(message)
            except WebsiteFetchFailedError as exc:
                message = f"Website research failed and was skipped: {exc}"
                warnings.append(message)
                research_warnings.append(message)
            else:
                extracted_text = research_result.extracted_text
                research_warnings = research_result.warnings
                warnings.extend(research_warnings)
                if "contact" in research_result.final_url.lower():
                    contact_page_url = research_result.final_url
            website_quality_level, website_quality_reasons = assess_website_quality(
                research_result, research_warnings
            )

        public_contact_email: str | None = None
        if self._settings.lead_sourcing_allow_public_website_email_extraction:
            public_contact_email = provider.extract_public_contact_info(
                extracted_text,
                allow_personal_emails=self._settings.lead_sourcing_allow_personal_emails,
            )

        # -- do-not-contact (never bypassable) -----------------------------------
        dnc_result = await self._compliance.check(
            email=public_contact_email,
            domain=enriched.company_domain,
            company_name=enriched.company_name,
        )
        if dnc_result.is_blocked:
            do_not_contact_status = "blocked"
            run.total_blocked_by_do_not_contact += 1
            warnings.append(dnc_result.warning_message)
            await self._audit.record(
                action="lead_candidate_blocked_by_do_not_contact",
                result="blocked",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="lead_candidate",
                entity_id=enriched.company_domain or enriched.company_name,
                request=http_request,
            )
        else:
            do_not_contact_status = "clear"

        # -- duplicate detection --------------------------------------------------
        existing_company: Company | None = None
        if enriched.company_domain:
            existing_company = await self._companies.find_by_domain(enriched.company_domain)
        if existing_company is None and enriched.company_name:
            existing_company = await self._companies.find_by_name(enriched.company_name)
        existing_candidate = await self._candidates.find_existing(
            company_domain=enriched.company_domain, company_name=enriched.company_name
        )
        is_duplicate = existing_company is not None or existing_candidate is not None
        duplicate_status = "duplicate" if is_duplicate else "new"
        crm_company_id = existing_company.id if existing_company is not None else None
        if is_duplicate:
            run.total_duplicates += 1
            warnings.append(
                "Possible duplicate: matches an existing CRM company or a "
                "previously sourced candidate."
            )
            await self._audit.record(
                action="lead_candidate_duplicate_detected",
                result="duplicate",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="lead_candidate",
                entity_id=enriched.company_domain or enriched.company_name,
                request=http_request,
            )

        # -- ICP scoring (never fabricates facts) ---------------------------------
        icp_fit_score: int | None = None
        icp_fit_level: str | None = None
        matched_signals: list[str] = []
        negative_signals: list[str] = []
        if campaign.icp_profile_id is not None:
            fit_result = await self._icp_service.check_fit(
                ICPFitCheckRequest(
                    icp_profile_id=campaign.icp_profile_id,
                    company_name=enriched.company_name,
                    industry=enriched.industry,
                    location=enriched.location,
                    website_text=extracted_text,
                    notes=enriched.description,
                )
            )
            icp_fit_score = fit_result.fit_score
            icp_fit_level = fit_result.fit_level
            matched_signals = fit_result.matched_signals
            negative_signals = fit_result.negative_signals
            warnings.extend(fit_result.warnings)
        else:
            warnings.append(
                "No ICP profile selected for this campaign — fit score was not computed."
            )

        run.total_candidates_found += 1

        candidate = LeadCandidate(
            sourcing_run_id=run.id,
            campaign_id=campaign.id,
            company_name=enriched.company_name,
            company_domain=enriched.company_domain,
            company_website_url=enriched.company_website_url,
            industry=enriched.industry,
            location=enriched.location,
            description=enriched.description,
            source_url=enriched.source_url,
            source_name=enriched.source_name,
            source_type=provider.name,
            public_contact_email=public_contact_email,
            contact_page_url=contact_page_url,
            confidence_score=enriched.confidence_score,
            icp_fit_score=icp_fit_score,
            icp_fit_level=icp_fit_level,
            matched_signals=matched_signals,
            negative_signals=negative_signals,
            website_quality_level=website_quality_level,
            website_quality_reasons=website_quality_reasons,
            do_not_contact_status=do_not_contact_status,
            duplicate_status=duplicate_status,
            review_status="pending",
            crm_company_id=crm_company_id,
            notes=notes,
            warnings=warnings,
        )

        if persist:
            candidate = await self._candidates.create(candidate)
            run.total_candidates_saved += 1

        return candidate

    # -- approve / reject -----------------------------------------------------------

    async def approve_candidate(
        self,
        candidate_id: UUID,
        request: ApproveLeadCandidateRequest,
        approved_by_user_id: UUID | None,
        approved_by_role: str | None,
        http_request: Request | None = None,
    ) -> ApproveLeadCandidateResponse:
        candidate = await self._candidates.get_by_id(candidate_id)
        if candidate is None:
            raise LeadCandidateNotFoundError(candidate_id)

        # Do-not-contact can never be bypassed, including from Lead Sourcing.
        if candidate.do_not_contact_status == "blocked":
            raise LeadCandidateBlockedError(candidate_id)

        warnings: list[str] = []
        if candidate.icp_fit_level in ("weak", "not_fit"):
            warnings.append(
                f"ICP fit is '{candidate.icp_fit_level}' — review carefully before "
                "any further outreach preparation."
            )

        company = await self._find_or_link_company(candidate)
        lead = await self._find_or_create_lead(company.id)

        candidate.review_status = "approved"
        candidate.crm_company_id = company.id
        candidate.crm_lead_id = lead.id
        if request.notes:
            candidate.notes = [*candidate.notes, request.notes]
        updated = await self._candidates.update(candidate)
        assert updated is not None

        await self._audit.record(
            action="lead_candidate_approved",
            result="success",
            actor_user_id=approved_by_user_id,
            actor_role=approved_by_role,
            entity_type="lead_candidate",
            entity_id=candidate_id,
            request=http_request,
        )
        await self._audit.record(
            action="lead_candidate_converted_to_crm",
            result="success",
            actor_user_id=approved_by_user_id,
            actor_role=approved_by_role,
            entity_type="lead_candidate",
            entity_id=candidate_id,
            metadata={"crm_company_id": str(company.id), "crm_lead_id": str(lead.id)},
            request=http_request,
        )

        return ApproveLeadCandidateResponse(
            candidate=LeadCandidateResponse.model_validate(updated),
            crm_company_id=company.id,
            crm_lead_id=lead.id,
            warnings=warnings,
        )

    async def reject_candidate(
        self,
        candidate_id: UUID,
        request: RejectLeadCandidateRequest,
        rejected_by_user_id: UUID | None,
        rejected_by_role: str | None,
        http_request: Request | None = None,
    ) -> RejectLeadCandidateResponse:
        candidate = await self._candidates.get_by_id(candidate_id)
        if candidate is None:
            raise LeadCandidateNotFoundError(candidate_id)

        candidate.review_status = "rejected"
        if request.reason:
            candidate.notes = [*candidate.notes, f"Rejected: {request.reason}"]
        updated = await self._candidates.update(candidate)
        assert updated is not None

        await self._audit.record(
            action="lead_candidate_rejected",
            result="success",
            actor_user_id=rejected_by_user_id,
            actor_role=rejected_by_role,
            entity_type="lead_candidate",
            entity_id=candidate_id,
            reason=request.reason,
            request=http_request,
        )

        return RejectLeadCandidateResponse(
            candidate=LeadCandidateResponse.model_validate(updated)
        )

    async def _find_or_link_company(self, candidate: LeadCandidate) -> Company:
        existing: Company | None = None
        if candidate.company_domain:
            existing = await self._companies.find_by_domain(candidate.company_domain)
        if existing is None and candidate.company_name:
            existing = await self._companies.find_by_name(candidate.company_name)
        if existing is not None:
            return existing
        return await self._companies.create(
            Company(
                name=candidate.company_name or candidate.company_domain or "Unknown",
                domain=candidate.company_domain,
                industry=candidate.industry,
            )
        )

    async def _find_or_create_lead(self, company_id: UUID) -> Lead:
        existing_leads = await self._leads.list_by_company(company_id, limit=1)
        if existing_leads:
            return existing_leads[0]
        # LeadSource is a native Postgres enum with no migration system in
        # this project (see backend/infrastructure/database/session.py's
        # create_all()) — reusing an existing value here (rather than
        # adding a new one) keeps this compatible with any database that
        # was already created before this feature shipped.
        return await self._leads.create(
            Lead(company_id=company_id, source=LeadSource.OTHER)
        )
