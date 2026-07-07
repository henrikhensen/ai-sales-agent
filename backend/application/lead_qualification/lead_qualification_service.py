"""Lead Qualification Service: scores and prioritizes Lead Candidates and
CRM Leads for human review.

Orchestrates the rule-based :class:`QualificationScoringService` (always
runs), the optional :class:`QualificationLLMAdvisor` (wording only, never
changes the score), the existing Do-not-contact, ICP, Offer, and Website
Research services. Never sends an email, never contacts anyone, never
starts a Sales Workflow, and never creates a draft — a qualification
result is a recommendation only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.lead_qualification.qualification_llm_advisor import (
    QualificationLLMAdvisor,
)
from backend.application.lead_qualification.qualification_scoring_service import (
    QualificationInput,
    QualificationScoringResult,
    QualificationScoringService,
)
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
from backend.application.research.exceptions import (
    InvalidWebsiteURLError,
    WebsiteFetchFailedError,
)
from backend.application.research.schemas import WebsiteResearchRequest
from backend.application.research.website_research_service import (
    WebsiteResearchService,
)
from backend.application.sales_strategy.icp_service import ICPService
from backend.application.sales_strategy.offer_service import OfferService
from backend.application.sales_strategy.schemas import ICPFitCheckRequest
from backend.domain.entities.company import Company
from backend.domain.entities.lead import Lead
from backend.domain.entities.lead_candidate import LeadCandidate
from backend.domain.entities.qualification_result import QualificationResult
from backend.domain.entities.qualification_run import QualificationRun
from backend.domain.enums import PipelineStatus
from backend.domain.exceptions import (
    ICPRequiredForQualificationError,
    LeadCandidateNotFoundError,
    OfferProfileNotFoundError,
    QualificationResultNotFoundError,
    QualificationRunNotFoundError,
    QualificationTargetNotFoundError,
)
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.lead_candidate_repository import (
    LeadCandidateRepository,
)
from backend.domain.repositories.lead_repository import LeadRepository
from backend.domain.repositories.qualification_result_repository import (
    QualificationResultRepository,
)
from backend.domain.repositories.qualification_run_repository import (
    QualificationRunRepository,
)
from backend.infrastructure.llm.factory import create_llm_provider
from backend.shared.config import Settings

#: Cap applied to any "qualify everything pending" batch when the caller
#: does not supply explicit ids — keeps one run bounded and predictable.
_DEFAULT_BATCH_LIMIT = 50

#: Results considered by the dashboard aggregation.
_DASHBOARD_SAMPLE_LIMIT = 500

#: Results eligible to appear in the dashboard's top-recommended list.
_TOP_RECOMMENDED_STATUSES = ("priority", "qualified")
_TOP_RECOMMENDED_LIMIT = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LeadQualificationService:
    def __init__(
        self,
        runs: QualificationRunRepository,
        results: QualificationResultRepository,
        lead_candidates: LeadCandidateRepository,
        companies: CompanyRepository,
        leads: LeadRepository,
        compliance: DoNotContactService,
        icp_service: ICPService,
        offer_service: OfferService,
        website_research: WebsiteResearchService,
        audit: AuditLogService,
        settings: Settings,
    ) -> None:
        self._runs = runs
        self._results = results
        self._lead_candidates = lead_candidates
        self._companies = companies
        self._leads = leads
        self._compliance = compliance
        self._icp_service = icp_service
        self._offer_service = offer_service
        self._website_research = website_research
        self._audit = audit
        self._settings = settings
        self._scoring = QualificationScoringService()

    # -- status / dashboard ----------------------------------------------------------

    async def get_status(self) -> LeadQualificationStatusResponse:
        warnings: list[str] = []
        if not self._settings.lead_qualification_enabled:
            warnings.append(
                "Lead Qualification is disabled (LEAD_QUALIFICATION_ENABLED=false)."
            )
        if self._settings.lead_qualification_use_llm:
            warnings.append(
                "LLM advisor is enabled — wording only, the score itself always "
                "stays rule-based."
            )
        return LeadQualificationStatusResponse(
            enabled=self._settings.lead_qualification_enabled,
            use_llm=self._settings.lead_qualification_use_llm,
            llm_provider=self._settings.llm_provider,
            llm_real_calls_enabled=self._settings.llm_enable_real_calls,
            use_website_research=self._settings.lead_qualification_use_website_research,
            require_icp=self._settings.lead_qualification_require_icp,
            default_min_score=self._settings.lead_qualification_default_min_score,
            priority_score=self._settings.lead_qualification_priority_score,
            disqualify_score=self._settings.lead_qualification_disqualify_score,
            warnings=warnings,
        )

    async def get_dashboard(self) -> QualificationDashboardResponse:
        sample = await self._results.list(limit=_DASHBOARD_SAMPLE_LIMIT)
        total_qualified = sum(1 for r in sample if r.qualification_status == "qualified")
        total_priority = sum(1 for r in sample if r.qualification_status == "priority")
        total_needs_review = sum(
            1 for r in sample if r.qualification_status == "needs_review"
        )
        total_disqualified = sum(
            1 for r in sample if r.qualification_status == "disqualified"
        )
        total_blocked = sum(1 for r in sample if r.qualification_status == "blocked")
        average_score = (
            sum(r.qualification_score for r in sample) / len(sample) if sample else None
        )

        top = sorted(
            (r for r in sample if r.qualification_status in _TOP_RECOMMENDED_STATUSES),
            key=lambda r: r.qualification_score,
            reverse=True,
        )[:_TOP_RECOMMENDED_LIMIT]

        warnings: list[str] = []
        if not sample:
            warnings.append("No qualification results yet — start a run to see data here.")

        return QualificationDashboardResponse(
            total_qualified=total_qualified,
            total_priority=total_priority,
            total_needs_review=total_needs_review,
            total_disqualified=total_disqualified,
            total_blocked=total_blocked,
            average_score=average_score,
            top_recommended_leads=[
                QualificationResultResponse.model_validate(r) for r in top
            ],
            warnings=warnings,
        )

    # -- listing ----------------------------------------------------------------------

    async def list_runs(
        self, limit: int = 100, offset: int = 0
    ) -> QualificationRunListResponse:
        runs = await self._runs.list(limit=limit, offset=offset)
        return QualificationRunListResponse(
            items=[QualificationRunResponse.model_validate(r) for r in runs],
            limit=limit,
            offset=offset,
        )

    async def get_run(self, run_id: UUID) -> QualificationRunResponse:
        run = await self._runs.get_by_id(run_id)
        if run is None:
            raise QualificationRunNotFoundError(run_id)
        return QualificationRunResponse.model_validate(run)

    async def list_results(
        self,
        limit: int = 100,
        offset: int = 0,
        qualification_run_id: UUID | None = None,
        qualification_status: str | None = None,
    ) -> QualificationResultListResponse:
        results = await self._results.list(
            limit=limit,
            offset=offset,
            qualification_run_id=qualification_run_id,
            qualification_status=qualification_status,
        )
        return QualificationResultListResponse(
            items=[QualificationResultResponse.model_validate(r) for r in results],
            limit=limit,
            offset=offset,
        )

    async def get_result(self, result_id: UUID) -> QualificationResultResponse:
        result = await self._results.get_by_id(result_id)
        if result is None:
            raise QualificationResultNotFoundError(result_id)
        return QualificationResultResponse.model_validate(result)

    # -- single-item qualify ------------------------------------------------------------

    async def qualify_lead_candidate(
        self,
        candidate_id: UUID,
        request: QualifyLeadCandidateRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> QualificationResultResponse:
        candidate = await self._lead_candidates.get_by_id(candidate_id)
        if candidate is None:
            raise LeadCandidateNotFoundError(candidate_id)

        run = await self._runs.create(
            QualificationRun(
                name=f"Qualify candidate: {candidate.company_name or candidate_id}",
                source_type="lead_candidate",
                icp_profile_id=request.icp_profile_id,
                offer_profile_id=request.offer_profile_id,
                status="running",
                started_by_user_id=actor_user_id,
                started_at=_now(),
            )
        )

        data, warnings = await self._build_input_for_candidate(
            candidate, icp_profile_id=request.icp_profile_id
        )
        result = await self._score_and_save(
            data,
            run,
            lead_candidate_id=candidate.id,
            company_id=candidate.crm_company_id,
            icp_profile_id=request.icp_profile_id,
            offer_profile_id=request.offer_profile_id,
            extra_warnings=warnings,
        )
        await self._finalize_run(run, [result])

        await self._audit.record(
            action="lead_candidate_qualified",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="lead_candidate",
            entity_id=candidate_id,
            metadata={
                "qualification_score": result.qualification_score,
                "qualification_status": result.qualification_status,
            },
            request=http_request,
        )
        if self._settings.lead_qualification_use_llm:
            await self._audit.record(
                action="qualification_llm_advisor_used",
                result="success",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="lead_candidate",
                entity_id=candidate_id,
                request=http_request,
            )

        return QualificationResultResponse.model_validate(result)

    async def qualify_crm_lead(
        self,
        lead_id: UUID,
        request: QualifyCRMLeadRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> QualificationResultResponse:
        lead = await self._leads.get(lead_id)
        if lead is None:
            raise QualificationTargetNotFoundError(lead_id)
        company = await self._companies.get(lead.company_id)
        if company is None:
            raise QualificationTargetNotFoundError(lead.company_id)

        run = await self._runs.create(
            QualificationRun(
                name=f"Qualify lead: {company.name}",
                source_type="crm_lead",
                icp_profile_id=request.icp_profile_id,
                offer_profile_id=request.offer_profile_id,
                status="running",
                started_by_user_id=actor_user_id,
                started_at=_now(),
            )
        )

        data, warnings = await self._build_input_for_lead(
            lead, company, icp_profile_id=request.icp_profile_id
        )
        result = await self._score_and_save(
            data,
            run,
            lead_id=lead.id,
            company_id=company.id,
            icp_profile_id=request.icp_profile_id,
            offer_profile_id=request.offer_profile_id,
            extra_warnings=warnings,
        )
        await self._advance_pipeline_if_eligible(lead, result)
        await self._finalize_run(run, [result])

        await self._audit.record(
            action="crm_lead_qualified",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="lead",
            entity_id=lead_id,
            metadata={
                "qualification_score": result.qualification_score,
                "qualification_status": result.qualification_status,
            },
            request=http_request,
        )
        if self._settings.lead_qualification_use_llm:
            await self._audit.record(
                action="qualification_llm_advisor_used",
                result="success",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="lead",
                entity_id=lead_id,
                request=http_request,
            )

        return QualificationResultResponse.model_validate(result)

    # -- batch run ---------------------------------------------------------------------

    async def start_run(
        self,
        request: StartLeadQualificationRequest,
        started_by_user_id: UUID | None,
        started_by_role: str | None,
        http_request: Request | None = None,
    ) -> StartLeadQualificationResponse:
        run = await self._runs.create(
            QualificationRun(
                name=request.name,
                source_type=request.source_type,
                icp_profile_id=request.icp_profile_id,
                offer_profile_id=request.offer_profile_id,
                status="running",
                started_by_user_id=started_by_user_id,
                started_at=_now(),
            )
        )
        await self._audit.record(
            action="qualification_run_started",
            result="started",
            actor_user_id=started_by_user_id,
            actor_role=started_by_role,
            entity_type="qualification_run",
            entity_id=run.id,
            metadata={"source_type": request.source_type, "dry_run": request.dry_run},
            request=http_request,
        )

        results: list[QualificationResult] = []
        run_warnings: list[str] = []

        try:
            if request.source_type in ("lead_candidate", "mixed"):
                candidates = await self._resolve_candidates(request.lead_candidate_ids)
                for candidate in candidates:
                    data, warnings = await self._build_input_for_candidate(
                        candidate, icp_profile_id=request.icp_profile_id
                    )
                    result = await self._score_and_save(
                        data,
                        run,
                        lead_candidate_id=candidate.id,
                        company_id=candidate.crm_company_id,
                        icp_profile_id=request.icp_profile_id,
                        offer_profile_id=request.offer_profile_id,
                        extra_warnings=warnings,
                        min_score_override=request.min_score,
                    )
                    results.append(result)

            if request.source_type in ("crm_lead", "mixed"):
                leads = await self._resolve_leads(request.lead_ids)
                for lead in leads:
                    company = await self._companies.get(lead.company_id)
                    if company is None:
                        run_warnings.append(
                            f"Lead {lead.id} has no matching company and was skipped."
                        )
                        continue
                    data, warnings = await self._build_input_for_lead(
                        lead, company, icp_profile_id=request.icp_profile_id
                    )
                    result = await self._score_and_save(
                        data,
                        run,
                        lead_id=lead.id,
                        company_id=company.id,
                        icp_profile_id=request.icp_profile_id,
                        offer_profile_id=request.offer_profile_id,
                        extra_warnings=warnings,
                        min_score_override=request.min_score,
                    )
                    if not request.dry_run:
                        await self._advance_pipeline_if_eligible(lead, result)
                    results.append(result)

            if request.source_type == "crm_company":
                companies = await self._resolve_companies(request.company_ids)
                for company in companies:
                    data, warnings = await self._build_input_for_lead(
                        None, company, icp_profile_id=request.icp_profile_id
                    )
                    result = await self._score_and_save(
                        data,
                        run,
                        company_id=company.id,
                        icp_profile_id=request.icp_profile_id,
                        offer_profile_id=request.offer_profile_id,
                        extra_warnings=warnings,
                        min_score_override=request.min_score,
                    )
                    results.append(result)
        except ICPRequiredForQualificationError as exc:
            run.status = "failed"
            run.completed_at = _now()
            run.warnings = [*run_warnings, str(exc)]
            await self._runs.update(run)
            await self._audit.record(
                action="qualification_run_failed",
                result="failed",
                actor_user_id=started_by_user_id,
                actor_role=started_by_role,
                entity_type="qualification_run",
                entity_id=run.id,
                reason=str(exc),
                request=http_request,
            )
            raise

        run.warnings = run_warnings
        await self._finalize_run(run, results)

        await self._audit.record(
            action="qualification_run_completed",
            result="success",
            actor_user_id=started_by_user_id,
            actor_role=started_by_role,
            entity_type="qualification_run",
            entity_id=run.id,
            metadata={
                "total_items": run.total_items,
                "qualified_count": run.qualified_count,
                "priority_count": run.priority_count,
                "dry_run": request.dry_run,
            },
            request=http_request,
        )

        return StartLeadQualificationResponse(
            run=QualificationRunResponse.model_validate(run),
            results=[QualificationResultResponse.model_validate(r) for r in results],
            dry_run=request.dry_run,
        )

    # -- review -----------------------------------------------------------------------

    async def review_result(
        self,
        result_id: UUID,
        request: QualificationReviewRequest,
        reviewed_by_user_id: UUID | None,
        reviewed_by_role: str | None,
        http_request: Request | None = None,
    ) -> QualificationReviewResponse:
        result = await self._results.get_by_id(result_id)
        if result is None:
            raise QualificationResultNotFoundError(result_id)

        # Do-not-contact can never be bypassed, including by a manual review.
        if result.compliance_status == "blocked" and request.qualification_status in (
            "qualified",
            "priority",
        ):
            result.qualification_status = "blocked"
        else:
            result.qualification_status = request.qualification_status
        if request.notes:
            result.fit_summary = (
                f"{result.fit_summary}\n\nReviewer note: {request.notes}"
                if result.fit_summary
                else f"Reviewer note: {request.notes}"
            )
        result.reviewed_by_user_id = reviewed_by_user_id
        result.reviewed_at = _now()
        updated = await self._results.update(result)
        assert updated is not None

        await self._audit.record(
            action="qualification_result_reviewed",
            result="success",
            actor_user_id=reviewed_by_user_id,
            actor_role=reviewed_by_role,
            entity_type="qualification_result",
            entity_id=result_id,
            metadata={"qualification_status": updated.qualification_status},
            request=http_request,
        )
        if updated.qualification_status == "priority":
            await self._audit.record(
                action="lead_marked_priority",
                result="success",
                actor_user_id=reviewed_by_user_id,
                actor_role=reviewed_by_role,
                entity_type="qualification_result",
                entity_id=result_id,
                request=http_request,
            )
        elif updated.qualification_status == "disqualified":
            await self._audit.record(
                action="lead_marked_disqualified",
                result="success",
                actor_user_id=reviewed_by_user_id,
                actor_role=reviewed_by_role,
                entity_type="qualification_result",
                entity_id=result_id,
                request=http_request,
            )

        return QualificationReviewResponse(
            result=QualificationResultResponse.model_validate(updated)
        )

    # -- input building -----------------------------------------------------------------

    async def _build_input_for_candidate(
        self, candidate: LeadCandidate, *, icp_profile_id: UUID | None
    ) -> tuple[QualificationInput, list[str]]:
        warnings: list[str] = []
        website_text = None

        if (
            self._settings.lead_qualification_use_website_research
            and candidate.company_website_url
        ):
            website_text, research_warnings = await self._research_website(
                candidate.company_website_url
            )
            warnings.extend(research_warnings)
        if not website_text:
            website_text = candidate.description

        icp_fit_score = candidate.icp_fit_score
        icp_fit_level = candidate.icp_fit_level
        icp_matched = list(candidate.matched_signals)
        icp_negative = list(candidate.negative_signals)

        if icp_profile_id is not None:
            icp_fit_score, icp_fit_level, icp_matched, icp_negative, fit_warnings = (
                await self._check_icp_fit(
                    icp_profile_id,
                    company_name=candidate.company_name,
                    industry=candidate.industry,
                    location=candidate.location,
                    website_text=website_text,
                    notes=candidate.description,
                )
            )
            warnings.extend(fit_warnings)
        elif icp_fit_score is None:
            if self._settings.lead_qualification_require_icp:
                raise ICPRequiredForQualificationError()
            warnings.append(
                "No ICP profile specified and no prior ICP fit data available."
            )

        # Do-not-contact is re-verified here (not just trusted from Lead
        # Sourcing time) since new opt-out entries may have been added since.
        dnc_result = await self._compliance.check(
            email=candidate.public_contact_email,
            domain=candidate.company_domain,
            company_name=candidate.company_name,
        )
        do_not_contact_status = "blocked" if dnc_result.is_blocked else "clear"

        data = QualificationInput(
            company_name=candidate.company_name,
            industry=candidate.industry,
            location=candidate.location,
            website_text=website_text,
            icp_fit_score=icp_fit_score,
            icp_fit_level=icp_fit_level,
            icp_matched_signals=icp_matched,
            icp_negative_signals=icp_negative,
            do_not_contact_status=do_not_contact_status,
            duplicate_status=candidate.duplicate_status,
            public_contact_email=candidate.public_contact_email,
            source_confidence=candidate.confidence_score,
        )
        return data, warnings

    async def _build_input_for_lead(
        self, lead: Lead | None, company: Company, *, icp_profile_id: UUID | None
    ) -> tuple[QualificationInput, list[str]]:
        warnings: list[str] = []
        website_text = None

        if self._settings.lead_qualification_use_website_research and company.domain:
            website_text, research_warnings = await self._research_website(
                f"https://{company.domain}"
            )
            warnings.extend(research_warnings)

        icp_fit_score = icp_fit_level = None
        icp_matched: list[str] = []
        icp_negative: list[str] = []

        if icp_profile_id is not None:
            icp_fit_score, icp_fit_level, icp_matched, icp_negative, fit_warnings = (
                await self._check_icp_fit(
                    icp_profile_id,
                    company_name=company.name,
                    industry=company.industry,
                    location=None,
                    website_text=website_text,
                    notes=None,
                )
            )
            warnings.extend(fit_warnings)
        elif self._settings.lead_qualification_require_icp:
            raise ICPRequiredForQualificationError()
        else:
            warnings.append("No ICP profile specified for this CRM lead/company.")

        dnc_result = await self._compliance.check(
            domain=company.domain, company_name=company.name
        )
        do_not_contact_status = "blocked" if dnc_result.is_blocked else "clear"

        data = QualificationInput(
            company_name=company.name,
            industry=company.industry,
            location=None,
            website_text=website_text,
            icp_fit_score=icp_fit_score,
            icp_fit_level=icp_fit_level,
            icp_matched_signals=icp_matched,
            icp_negative_signals=icp_negative,
            do_not_contact_status=do_not_contact_status,
            duplicate_status="unknown",
            public_contact_email=None,
            source_confidence=None,
            pipeline_status=lead.pipeline_status.value if lead is not None else None,
        )
        return data, warnings

    async def _check_icp_fit(
        self,
        icp_profile_id: UUID,
        *,
        company_name: str | None,
        industry: str | None,
        location: str | None,
        website_text: str | None,
        notes: str | None,
    ) -> tuple[int, str, list[str], list[str], list[str]]:
        fit_result = await self._icp_service.check_fit(
            ICPFitCheckRequest(
                icp_profile_id=icp_profile_id,
                company_name=company_name,
                industry=industry,
                location=location,
                website_text=website_text,
                notes=notes,
            )
        )
        return (
            fit_result.fit_score,
            fit_result.fit_level,
            fit_result.matched_signals,
            fit_result.negative_signals,
            fit_result.warnings,
        )

    async def _research_website(self, url: str) -> tuple[str | None, list[str]]:
        try:
            research = await self._website_research.research(
                WebsiteResearchRequest(url=url, max_pages=1, include_same_domain_links=False)
            )
        except InvalidWebsiteURLError as exc:
            return None, [f"Website could not be researched: {exc}"]
        except WebsiteFetchFailedError as exc:
            return None, [f"Website research failed and was skipped: {exc}"]
        return research.extracted_text, list(research.warnings)

    # -- resolving batch targets ---------------------------------------------------------

    async def _resolve_candidates(self, ids: list[UUID]) -> list[LeadCandidate]:
        if ids:
            candidates = []
            for candidate_id in ids:
                candidate = await self._lead_candidates.get_by_id(candidate_id)
                if candidate is not None:
                    candidates.append(candidate)
            return candidates
        return await self._lead_candidates.list(
            limit=_DEFAULT_BATCH_LIMIT, review_status="pending"
        )

    async def _resolve_leads(self, ids: list[UUID]) -> list[Lead]:
        if ids:
            leads = []
            for lead_id in ids:
                lead = await self._leads.get(lead_id)
                if lead is not None:
                    leads.append(lead)
            return leads
        return await self._leads.list(limit=_DEFAULT_BATCH_LIMIT)

    async def _resolve_companies(self, ids: list[UUID]) -> list[Company]:
        if ids:
            companies = []
            for company_id in ids:
                company = await self._companies.get(company_id)
                if company is not None:
                    companies.append(company)
            return companies
        return await self._companies.list(limit=_DEFAULT_BATCH_LIMIT)

    # -- scoring / persistence ------------------------------------------------------------

    async def _score_and_save(
        self,
        data: QualificationInput,
        run: QualificationRun,
        *,
        lead_candidate_id: UUID | None = None,
        lead_id: UUID | None = None,
        company_id: UUID | None = None,
        icp_profile_id: UUID | None = None,
        offer_profile_id: UUID | None = None,
        extra_warnings: list[str] | None = None,
        min_score_override: int | None = None,
    ) -> QualificationResult:
        min_score = min_score_override or self._settings.lead_qualification_default_min_score
        scoring_result = self._scoring.score(
            data,
            min_score=min_score,
            priority_score=self._settings.lead_qualification_priority_score,
            disqualify_score=self._settings.lead_qualification_disqualify_score,
        )

        if self._settings.lead_qualification_use_llm:
            scoring_result = await self._enhance_with_llm(
                scoring_result,
                data=data,
                offer_profile_id=offer_profile_id,
            )

        all_missing_data = list(
            dict.fromkeys([*scoring_result.missing_data, *(extra_warnings or [])])
        )

        result = QualificationResult(
            qualification_run_id=run.id,
            lead_candidate_id=lead_candidate_id,
            lead_id=lead_id,
            company_id=company_id,
            icp_profile_id=icp_profile_id,
            offer_profile_id=offer_profile_id,
            qualification_score=scoring_result.score,
            qualification_level=scoring_result.level,
            qualification_status=scoring_result.status,
            fit_summary=scoring_result.fit_summary,
            score_breakdown=scoring_result.breakdown.model_dump(),
            positive_signals=scoring_result.positive_signals,
            negative_signals=scoring_result.negative_signals,
            missing_data=all_missing_data,
            recommended_next_action=scoring_result.recommended_next_action,
            recommended_outreach_angle=scoring_result.recommended_outreach_angle,
            disqualification_reason=scoring_result.disqualification_reason,
            compliance_status="blocked" if data.do_not_contact_status == "blocked" else "clear",
            do_not_contact_status=data.do_not_contact_status,
            duplicate_status=data.duplicate_status,
            pipeline_status=data.pipeline_status,
            confidence_score=data.source_confidence,
        )
        return await self._results.create(result)

    async def _enhance_with_llm(
        self,
        scoring_result: QualificationScoringResult,
        *,
        data: QualificationInput,
        offer_profile_id: UUID | None,
    ) -> QualificationScoringResult:
        offer_value_proposition = None
        offer_forbidden_claims = None
        if offer_profile_id is not None:
            try:
                offer = await self._offer_service.get_entity(offer_profile_id)
                offer_value_proposition = offer.main_value_proposition
                offer_forbidden_claims = offer.forbidden_claims
            except OfferProfileNotFoundError:
                pass

        llm = create_llm_provider(self._settings)
        advisor = QualificationLLMAdvisor(
            llm, max_notes_chars=self._settings.lead_qualification_max_notes_chars
        )
        return await advisor.enhance(
            scoring_result,
            company_name=data.company_name,
            industry=data.industry,
            offer_value_proposition=offer_value_proposition,
            offer_forbidden_claims=offer_forbidden_claims,
        )

    async def _advance_pipeline_if_eligible(
        self, lead: Lead, result: QualificationResult
    ) -> None:
        # Bookkeeping only — never contacts anyone. Only advances a lead
        # that is still brand new, and only for outcomes worth pursuing;
        # blocked/disqualified/duplicate leads are left untouched.
        if lead.pipeline_status != PipelineStatus.NEW:
            return
        if result.qualification_status not in ("qualified", "priority"):
            return
        await self._leads.update_pipeline_status(lead.id, PipelineStatus.RESEARCH_COMPLETED)

    async def _finalize_run(
        self, run: QualificationRun, results: list[QualificationResult]
    ) -> None:
        ranked = sorted(results, key=lambda r: r.qualification_score, reverse=True)
        for index, result in enumerate(ranked, start=1):
            result.priority_rank = index
            await self._results.update(result)

        run.status = "completed"
        run.completed_at = _now()
        run.total_items = len(results)
        run.qualified_count = sum(1 for r in results if r.qualification_status == "qualified")
        run.priority_count = sum(1 for r in results if r.qualification_status == "priority")
        run.disqualified_count = sum(
            1 for r in results if r.qualification_status == "disqualified"
        )
        run.needs_review_count = sum(
            1 for r in results if r.qualification_status == "needs_review"
        )
        run.average_score = (
            sum(r.qualification_score for r in results) / len(results) if results else None
        )
        await self._runs.update(run)
