"""Real-World Test Mode (Phase 34): a controlled test run against a real
lead/candidate and, optionally, a real website and real LLM output.

This is a thin, auditable wrapper around the existing Sales Workflow — it
never duplicates Lead Research, Company Intelligence, Personalization, or
Email Draft logic, and it inherits every one of the Sales Workflow's
existing safety guarantees: no email is ever sent, no external draft is
created automatically, Do-not-contact is always checked, and Human
Review is never bypassed. "Completed" here never means anything was
sent — the produced email draft still needs Human Review like any other.

``mode`` only ever governs how much of a run is allowed to touch real
external systems:
  - "safe": never fetches a real website, even if a URL is given.
  - "mock": may fetch a real, public website (never anything requiring a
    login or behind a paywall) but does not itself force real LLM output.
  - "real_llm": same as "mock", but requires the system to already be
    explicitly configured for real LLM calls (``LLM_ENABLE_REAL_CALLS``)
    — refused outright otherwise, never silently downgraded.

Since the LLM provider is a single, globally-configured dependency (not
swapped per request), "safe"/"mock" runs on a system that is *itself*
globally configured for real LLM calls will still produce real LLM
output; this is surfaced as an explicit warning rather than silently
pretended away.
"""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse
from uuid import UUID

from fastapi import Request

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.real_world_test.schemas import (
    CreateRealWorldTestRunRequest,
    RealWorldTestRunListResponse,
    RealWorldTestRunResponse,
)
from backend.application.sales_strategy.offer_service import OfferService
from backend.application.workflows.exceptions import WorkflowStepError
from backend.application.workflows.sales_workflow import SalesWorkflowService
from backend.application.workflows.schemas import SalesWorkflowRequest
from backend.domain.entities.real_world_test_run import RealWorldTestRun
from backend.domain.exceptions import (
    InvalidRealWorldTestRunTransitionError,
    OfferProfileNotFoundError,
    RealWorldTestModeNotAllowedError,
    RealWorldTestRunNotFoundError,
)
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.lead_candidate_repository import (
    LeadCandidateRepository,
)
from backend.domain.repositories.lead_repository import LeadRepository
from backend.domain.repositories.quality_score_repository import (
    QualityScoreRepository,
)
from backend.domain.repositories.real_world_test_run_repository import (
    RealWorldTestRunRepository,
)
from backend.shared.config import Settings

_TERMINAL_STATUSES = {"completed", "blocked", "failed", "aborted"}


class RealWorldTestRunService:
    def __init__(
        self,
        test_runs: RealWorldTestRunRepository,
        lead_candidates: LeadCandidateRepository,
        leads: LeadRepository,
        companies: CompanyRepository,
        quality_scores: QualityScoreRepository,
        compliance: DoNotContactService,
        offer_service: OfferService,
        sales_workflow: SalesWorkflowService,
        audit: AuditLogService,
        settings: Settings,
    ) -> None:
        self._test_runs = test_runs
        self._lead_candidates = lead_candidates
        self._leads = leads
        self._companies = companies
        self._quality_scores = quality_scores
        self._compliance = compliance
        self._offer_service = offer_service
        self._sales_workflow = sales_workflow
        self._audit = audit
        self._settings = settings

    # -- create -----------------------------------------------------------------------

    async def create_run(
        self,
        request: CreateRealWorldTestRunRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> RealWorldTestRunResponse:
        if request.mode == "real_llm" and not self._settings.llm_enable_real_calls:
            await self._audit.record(
                action="real_world_test_run_blocked",
                result="blocked",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="real_world_test_run",
                reason="mode='real_llm' requested without LLM_ENABLE_REAL_CALLS.",
                request=http_request,
            )
            raise RealWorldTestModeNotAllowedError()

        company_name, industry, website_url, domain, resolution_warnings = (
            await self._resolve_target(request)
        )

        product_or_service_offered = request.product_or_service_offered
        offer_warnings: list[str] = []
        if not product_or_service_offered and request.offer_profile_id is not None:
            try:
                offer = await self._offer_service.get_entity(request.offer_profile_id)
                product_or_service_offered = offer.main_value_proposition
            except OfferProfileNotFoundError:
                offer_warnings.append(
                    f"Offer profile {request.offer_profile_id} was not found; "
                    "used a generic placeholder instead."
                )
        if not product_or_service_offered:
            product_or_service_offered = "unser Angebot"

        mode_warnings: list[str] = []
        if request.mode in ("safe", "mock") and self._settings.llm_enable_real_calls:
            mode_warnings.append(
                f"mode='{request.mode}' was requested, but this system is "
                "currently globally configured for real LLM calls "
                "(LLM_ENABLE_REAL_CALLS=true) — no per-run override exists, "
                "so this run's LLM output may still be real."
            )

        input_snapshot = {
            "name": request.name,
            "mode": request.mode,
            "lead_candidate_id": str(request.lead_candidate_id)
            if request.lead_candidate_id
            else None,
            "lead_id": str(request.lead_id) if request.lead_id else None,
            "icp_profile_id": str(request.icp_profile_id)
            if request.icp_profile_id
            else None,
            "offer_profile_id": str(request.offer_profile_id)
            if request.offer_profile_id
            else None,
            "company_name": company_name,
            "website_url": website_url,
            "industry": industry,
            "product_or_service_offered": product_or_service_offered,
            "notes": request.notes,
        }

        run = await self._test_runs.create(
            RealWorldTestRun(
                name=request.name,
                status="running",
                mode=request.mode,
                lead_candidate_id=request.lead_candidate_id,
                lead_id=request.lead_id,
                icp_profile_id=request.icp_profile_id,
                offer_profile_id=request.offer_profile_id,
                input_snapshot=input_snapshot,
                warnings=[*resolution_warnings, *offer_warnings, *mode_warnings],
                created_by_user_id=actor_user_id,
            )
        )

        await self._audit.record(
            action="real_world_test_run_created",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="real_world_test_run",
            entity_id=run.id,
            metadata={"mode": request.mode},
            request=http_request,
        )

        # Do-not-contact is always checked here — never trusted from the
        # candidate/lead alone, and never bypassed by any mode.
        dnc = await self._compliance.check(domain=domain, company_name=company_name)
        if dnc.is_blocked:
            run.status = "blocked"
            run.warnings.append(
                "Blocked by an active do-not-contact entry — the Sales "
                "Workflow was not started."
            )
            updated = await self._test_runs.update(run)
            assert updated is not None
            await self._audit.record(
                action="real_world_test_run_blocked",
                result="blocked",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="real_world_test_run",
                entity_id=run.id,
                reason="do_not_contact",
                request=http_request,
            )
            return RealWorldTestRunResponse.model_validate(updated)

        workflow_request = SalesWorkflowRequest(
            company_name=company_name,
            website_url=website_url if website_url else None,
            industry=industry,
            product_or_service_offered=product_or_service_offered,
            notes=request.notes,
            use_website_research=bool(website_url) and request.mode != "safe",
            icp_profile_id=request.icp_profile_id,
            offer_profile_id=request.offer_profile_id,
        )

        try:
            result = await self._sales_workflow.run(workflow_request)
        except WorkflowStepError as exc:
            run.status = "failed"
            run.errors.append(f"Sales Workflow step failed: {exc}")
            updated = await self._test_runs.update(run)
            assert updated is not None
            await self._audit.record(
                action="real_world_test_run_failed",
                result="failed",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                entity_type="real_world_test_run",
                entity_id=run.id,
                reason=str(exc),
                request=http_request,
            )
            return RealWorldTestRunResponse.model_validate(updated)

        run.result_snapshot = result.model_dump(mode="json")
        run.workflow_run_id = UUID(result.workflow_id) if result.workflow_id else None

        if result.status == "blocked":
            run.status = "blocked"
            run.warnings.append(
                "Blocked by do-not-contact inside the Sales Workflow itself."
            )
        else:
            run.status = "completed"
            if run.workflow_run_id is not None:
                latest_score = await self._quality_scores.find_latest_for_entity(
                    "workflow_run", run.workflow_run_id
                )
                if latest_score is not None:
                    run.quality_score_id = latest_score.id
            if result.quality_warnings:
                run.warnings.extend(result.quality_warnings)

        updated = await self._test_runs.update(run)
        assert updated is not None

        await self._audit.record(
            action="real_world_test_run_completed"
            if run.status == "completed"
            else "real_world_test_run_blocked",
            result="success" if run.status == "completed" else "blocked",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="real_world_test_run",
            entity_id=run.id,
            metadata={
                "workflow_run_id": str(run.workflow_run_id)
                if run.workflow_run_id
                else None,
                "status": run.status,
            },
            request=http_request,
        )
        return RealWorldTestRunResponse.model_validate(updated)

    async def _resolve_target(
        self, request: CreateRealWorldTestRunRequest
    ) -> tuple[str, str | None, str | None, str | None, list[str]]:
        """Resolve (company_name, industry, website_url, domain, warnings).

        ``domain`` always falls back to whatever can be derived from the
        final ``website_url`` if it wasn't already known from a
        candidate/company — the do-not-contact check must never be
        skipped just because no CRM/candidate record was linked.
        """
        warnings: list[str] = []
        company_name: str | None = None
        industry: str | None = None
        website_url = request.website_url
        domain: str | None = None

        if request.lead_candidate_id is not None:
            candidate = await self._lead_candidates.get_by_id(request.lead_candidate_id)
            if candidate is None:
                warnings.append(
                    f"Lead candidate {request.lead_candidate_id} was not found; "
                    "falling back to directly-provided fields."
                )
            else:
                company_name = candidate.company_name
                industry = candidate.industry
                website_url = website_url or candidate.company_website_url
                domain = candidate.company_domain

        if company_name is None and request.lead_id is not None:
            lead = await self._leads.get(request.lead_id)
            if lead is None:
                warnings.append(
                    f"Lead {request.lead_id} was not found; falling back to "
                    "directly-provided fields."
                )
            else:
                company = await self._companies.get(lead.company_id)
                if company is not None:
                    company_name = company.name
                    industry = company.industry
                    domain = company.domain
                else:
                    warnings.append(
                        f"Lead {request.lead_id}'s company was not found; "
                        "falling back to directly-provided fields."
                    )

        company_name = request.company_name or company_name
        industry = request.industry or industry
        if company_name is None:
            warnings.append(
                "No lead/candidate could be resolved and no company_name was "
                "given — using a placeholder."
            )
            company_name = "Unknown company"

        if domain is None and website_url:
            domain = urlparse(website_url).hostname

        return (company_name, industry, website_url, domain, warnings)

    # -- read -----------------------------------------------------------------------

    async def list_runs(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        created_by_user_id: UUID | None = None,
    ) -> RealWorldTestRunListResponse:
        items = await self._test_runs.list(
            limit=limit,
            offset=offset,
            status=status,
            created_by_user_id=created_by_user_id,
        )
        return RealWorldTestRunListResponse(
            items=[RealWorldTestRunResponse.model_validate(r) for r in items],
            limit=limit,
            offset=offset,
        )

    async def _get_or_404(self, run_id: UUID) -> RealWorldTestRun:
        run = await self._test_runs.get_by_id(run_id)
        if run is None:
            raise RealWorldTestRunNotFoundError(run_id)
        return run

    async def get_run(self, run_id: UUID) -> RealWorldTestRunResponse:
        run = await self._get_or_404(run_id)
        return RealWorldTestRunResponse.model_validate(run)

    # -- abort ------------------------------------------------------------------------

    async def abort_run(
        self,
        run_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> RealWorldTestRunResponse:
        run = await self._get_or_404(run_id)
        if run.status in _TERMINAL_STATUSES:
            raise InvalidRealWorldTestRunTransitionError(run.status)
        run.status = "aborted"
        run.aborted_at = datetime.now(timezone.utc)
        updated = await self._test_runs.update(run)
        assert updated is not None
        await self._audit.record(
            action="real_world_test_run_aborted",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="real_world_test_run",
            entity_id=run.id,
            request=http_request,
        )
        return RealWorldTestRunResponse.model_validate(updated)
