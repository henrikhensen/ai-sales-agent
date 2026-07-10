"""End-to-end Sales Workflow: orchestrates existing agents in sequence.

``SalesWorkflowService`` runs Lead Research, Company Intelligence,
Personalization, and Email Draft one after another, mapping each step's
output into the next step's input, then produces a human-review summary. It
builds no new agents and calls no external services beyond what each
existing agent service already does (the mock provider by default).

This workflow never sends an email, contacts anyone, or books a meeting —
it only ever produces analysis and a draft, with human review mandatory.
Every completed run is persisted via :class:`WorkflowHistoryService` so it
can be reviewed later; the response's ``workflow_id`` is the id of that
saved record.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from pydantic import ValidationError

from backend.agents.company_intelligence.exceptions import (
    InvalidCompanyIntelligenceOutputError,
)
from backend.agents.company_intelligence.schemas import (
    CompanyIntelligenceRequest,
    CompanyIntelligenceResponse,
)
from backend.agents.company_intelligence.service import CompanyIntelligenceService
from backend.agents.email_draft.exceptions import InvalidEmailDraftOutputError
from backend.agents.email_draft.schemas import EmailDraftRequest, EmailDraftResponse
from backend.agents.email_draft.service import EmailDraftService
from backend.agents.lead_research.exceptions import InvalidLeadResearchOutputError
from backend.agents.lead_research.schemas import (
    LeadResearchRequest,
    LeadResearchResponse,
)
from backend.agents.lead_research.service import LeadResearchService
from backend.agents.personalization.exceptions import (
    InvalidPersonalizationOutputError,
)
from backend.agents.personalization.schemas import (
    PersonalizationRequest,
    PersonalizationResponse,
)
from backend.agents.personalization.service import PersonalizationService
from backend.application.compliance.do_not_contact_service import DoNotContactService
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
from backend.application.sales_strategy.offer_service import OfferService
from backend.application.sales_strategy.schemas import ICPFitCheckRequest
from backend.application.workflows.exceptions import (
    WebsiteResearchBlockedError,
    WorkflowStepError,
)
from backend.application.quality.quality_scoring_service import QualityScoringService
from backend.application.workflows.history_service import WorkflowHistoryService
from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)
from backend.infrastructure.llm.base import LLMError
from backend.shared.config import Settings

if TYPE_CHECKING:
    # Deferred to break an import cycle: WorkflowCrmSyncService depends on
    # this module's SalesWorkflowRequest/Response schemas. Safe at runtime
    # because `from __future__ import annotations` makes this a string
    # annotation only, never evaluated.
    from backend.application.crm.workflow_sync_service import WorkflowCrmSyncService

_COMPLIANCE_NOTE = (
    "This workflow produced analysis and a draft only. No email was sent, no "
    "contact was made, and no meeting was booked automatically. A human must "
    "review every step below — especially 'claims_to_verify' and "
    "'do_not_send_if' in the email draft — before any outreach happens."
)


class SalesWorkflowService:
    """Runs the existing agent services in sequence and aggregates the result."""

    def __init__(
        self,
        lead_research: LeadResearchService,
        company_intelligence: CompanyIntelligenceService,
        personalization: PersonalizationService,
        email_draft: EmailDraftService,
        history: WorkflowHistoryService,
        crm_sync: WorkflowCrmSyncService,
        website_research: WebsiteResearchService,
        compliance: DoNotContactService,
        icp_service: ICPService,
        offer_service: OfferService,
        quality_scoring: QualityScoringService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._lead_research = lead_research
        self._company_intelligence = company_intelligence
        self._personalization = personalization
        self._email_draft = email_draft
        self._history = history
        self._crm_sync = crm_sync
        self._website_research = website_research
        self._icp_service = icp_service
        self._offer_service = offer_service
        self._compliance = compliance
        self._quality_scoring = quality_scoring
        self._settings = settings

    async def run(self, request: SalesWorkflowRequest) -> SalesWorkflowResponse:
        """Execute all four steps and return a human-review summary.

        Raises:
            WorkflowStepError: if any step's output fails validation (e.g. the
                configured LLM provider returned malformed JSON).
            WebsiteResearchBlockedError: if website research was requested
                for a blocked/invalid URL — a security-relevant failure,
                unlike an ordinary fetch problem (see below), which never
                aborts the workflow.
        """
        website_research_used = False
        website_research_result: WebsiteResearchResponse | None = None
        website_research_warnings: list[str] = []

        if request.use_website_research and request.website_url:
            website_research_input = WebsiteResearchRequest(
                url=str(request.website_url),
                max_pages=request.website_research_max_pages or 1,
                include_same_domain_links=False,
            )
            try:
                result = await self._website_research.research(website_research_input)
            except InvalidWebsiteURLError as exc:
                # A blocked or invalid URL is a security-relevant signal (the
                # caller asked us to fetch something we refuse to touch), not
                # an ordinary fetch problem — abort instead of continuing
                # silently. A distinct exception type (rather than
                # WorkflowStepError) lets the API layer respond with a clean
                # 400 that never echoes the internal reason to the client.
                raise WebsiteResearchBlockedError(str(exc)) from exc
            except WebsiteFetchFailedError as exc:
                website_research_warnings.append(
                    f"Website research failed and was skipped: {exc}"
                )
            else:
                website_research_result = result
                website_research_used = True
                website_research_warnings.extend(result.warnings)

        # Prefer text the caller already supplied; only fall back to the
        # freshly fetched page, and never fabricate anything otherwise.
        effective_website_text = request.website_text
        if not effective_website_text and website_research_result is not None:
            effective_website_text = website_research_result.extracted_text

        try:
            lead_research = await self._lead_research.research(
                LeadResearchRequest(
                    company_name=request.company_name,
                    website_url=request.website_url,
                    industry=request.industry,
                    location=request.location,
                    notes=request.notes,
                )
            )
        except InvalidLeadResearchOutputError as exc:
            raise WorkflowStepError("lead_research", exc.reason) from exc
        except LLMError as exc:
            raise WorkflowStepError("lead_research", str(exc)) from exc

        try:
            company_intelligence = await self._company_intelligence.analyze(
                CompanyIntelligenceRequest(
                    company_name=request.company_name,
                    website_url=request.website_url,
                    industry=request.industry,
                    location=request.location,
                    company_description=request.company_description,
                    website_text=effective_website_text,
                    notes=request.notes,
                )
            )
        except InvalidCompanyIntelligenceOutputError as exc:
            raise WorkflowStepError("company_intelligence", exc.reason) from exc
        except LLMError as exc:
            raise WorkflowStepError("company_intelligence", str(exc)) from exc

        # Optional ICP fit assessment — pure analysis over data already
        # available in this run (never a new fetch/scrape), so it runs
        # regardless of do-not-contact status, just like Lead Research and
        # Company Intelligence above. A missing icp_profile_id is the
        # normal case: the workflow behaves identically without one.
        icp_fit_score: int | None = None
        icp_fit_level: str | None = None
        icp_fit_summary: str | None = None
        icp_warnings: list[str] = []
        if request.icp_profile_id is not None:
            icp_fit_result = await self._icp_service.check_fit(
                ICPFitCheckRequest(
                    icp_profile_id=request.icp_profile_id,
                    company_name=request.company_name,
                    industry=request.industry,
                    location=request.location,
                    website_text=effective_website_text,
                    notes=request.notes,
                )
            )
            icp_fit_score = icp_fit_result.fit_score
            icp_fit_level = icp_fit_result.fit_level
            icp_fit_summary = icp_fit_result.recommendation
            icp_warnings = icp_fit_result.warnings

        # Opt-out takes precedence over the rest of the workflow: Lead
        # Research and Company Intelligence are pure analysis and are
        # allowed to complete either way, but a do-not-contact match stops
        # outreach preparation here — no Personalization strategy and no
        # Email Draft are produced. This can never be bypassed from within
        # the workflow itself.
        website_domain = (
            request.website_url.host if request.website_url is not None else None
        )
        do_not_contact_block = await self._compliance.check(
            email=request.recipient_email,
            domain=website_domain,
            company_name=request.company_name,
        )

        if do_not_contact_block.is_blocked:
            response = SalesWorkflowResponse(
                workflow_id=str(uuid.uuid4()),
                status="blocked",
                company_name=request.company_name,
                lead_research=lead_research,
                company_intelligence=company_intelligence,
                personalization=None,
                email_draft=None,
                do_not_contact_block=do_not_contact_block,
                human_review_required=True,
                review_checklist=[
                    "This lead is on the do-not-contact list — no outreach "
                    "may be prepared or sent for it.",
                ],
                compliance_notes=[
                    _COMPLIANCE_NOTE,
                    f"Do-not-contact blockiert Outreach: {do_not_contact_block.warning_message}",
                ],
                missing_information=self._collect_missing_information_partial(
                    lead_research, company_intelligence
                ),
                confidence_score=self._aggregate_confidence_partial(
                    lead_research, company_intelligence
                ),
                website_research_used=website_research_used,
                website_research=(
                    website_research_result.model_dump(mode="json")
                    if website_research_result is not None
                    else None
                ),
                website_research_warnings=website_research_warnings,
                icp_profile_id=(
                    str(request.icp_profile_id) if request.icp_profile_id else None
                ),
                icp_fit_score=icp_fit_score,
                icp_fit_level=icp_fit_level,
                icp_fit_summary=icp_fit_summary,
                icp_warnings=icp_warnings,
            )
        else:
            # Optional Offer context: only ever adds notes/known-pain-points
            # context to the existing agent steps below — never invents a
            # fact, never guarantees an outcome, and forbidden_claims are
            # explicitly called out so the LLM avoids them.
            offer_notes_parts: list[str] = []
            offer_known_pain_points: list[str] = list(lead_research.likely_pain_points)
            offer_summary: str | None = None
            offer_warnings: list[str] = []
            if request.offer_profile_id is not None:
                offer = await self._offer_service.get_entity(request.offer_profile_id)
                offer_notes_parts.append(f"Value proposition: {offer.main_value_proposition}")
                if offer.key_benefits:
                    offer_notes_parts.append(
                        "Key benefits to mention: " + "; ".join(offer.key_benefits)
                    )
                if offer.differentiators:
                    offer_notes_parts.append(
                        "Differentiators to mention: " + "; ".join(offer.differentiators)
                    )
                if offer.call_to_action:
                    offer_notes_parts.append(f"Suggested CTA: {offer.call_to_action}")
                if offer.forbidden_claims:
                    offer_notes_parts.append(
                        "Never state or imply any of these claims: "
                        + "; ".join(offer.forbidden_claims)
                    )
                if offer.required_disclaimers:
                    offer_notes_parts.append(
                        "Include these disclaimers if relevant: "
                        + "; ".join(offer.required_disclaimers)
                    )
                offer_known_pain_points.extend(offer.pain_points_solved)

                offer_summary_parts = [offer.main_value_proposition]
                if offer.key_benefits:
                    offer_summary_parts.append(
                        "Key benefits: " + "; ".join(offer.key_benefits)
                    )
                offer_summary = " ".join(offer_summary_parts)
                if not offer.proof_points:
                    offer_warnings.append(
                        "No proof_points are defined for this offer — avoid "
                        "implying credibility that hasn't been established."
                    )
                if not offer.is_active:
                    offer_warnings.append(
                        "This offer profile is deactivated — review before using it."
                    )

            if icp_fit_level in ("weak", "not_fit"):
                offer_notes_parts.append(
                    f"ICP fit is '{icp_fit_level}' for this lead — keep the "
                    "tone exploratory and low-pressure rather than a "
                    "confident, aggressive pitch."
                )

            combined_notes = request.notes
            if offer_notes_parts:
                offer_notes_block = " ".join(offer_notes_parts)
                combined_notes = (
                    f"{request.notes}\n\n{offer_notes_block}"
                    if request.notes
                    else offer_notes_block
                )

            try:
                personalization = await self._personalization.personalize(
                    PersonalizationRequest(
                        company_name=request.company_name,
                        website_url=request.website_url,
                        industry=request.industry,
                        location=request.location,
                        lead_summary=lead_research.short_summary,
                        company_intelligence_summary=company_intelligence.business_summary,
                        target_persona=request.target_persona,
                        product_or_service_offered=request.product_or_service_offered,
                        known_pain_points=offer_known_pain_points,
                        notes=combined_notes,
                    )
                )
            except InvalidPersonalizationOutputError as exc:
                raise WorkflowStepError("personalization", exc.reason) from exc
            except LLMError as exc:
                raise WorkflowStepError("personalization", str(exc)) from exc

            try:
                email_draft_request = EmailDraftRequest(
                    company_name=request.company_name,
                    website_url=request.website_url,
                    industry=request.industry,
                    recipient_role=request.target_persona,
                    recipient_name=request.recipient_name,
                    sender_name=request.sender_name,
                    sender_company=request.sender_company,
                    product_or_service_offered=request.product_or_service_offered,
                    personalization_summary=personalization.personalization_summary,
                    relevant_observations=personalization.relevant_observations,
                    pain_point_angles=personalization.pain_point_angles,
                    value_arguments=personalization.value_arguments,
                    credibility_points=personalization.credibility_points,
                    suggested_ctas=personalization.suggested_ctas,
                    tone=request.tone,
                    language=request.language,
                    notes=combined_notes,
                )
            except ValidationError as exc:
                raise WorkflowStepError("email_draft", str(exc)) from exc

            try:
                email_draft = await self._email_draft.draft(email_draft_request)
            except InvalidEmailDraftOutputError as exc:
                raise WorkflowStepError("email_draft", exc.reason) from exc
            except LLMError as exc:
                raise WorkflowStepError("email_draft", str(exc)) from exc

            review_checklist = self._build_review_checklist(email_draft)
            if icp_fit_level in ("weak", "not_fit"):
                review_checklist.insert(
                    0,
                    f"ICP fit is '{icp_fit_level}' — reconsider whether "
                    "aggressive outreach is appropriate for this lead.",
                )

            response = SalesWorkflowResponse(
                workflow_id=str(uuid.uuid4()),
                status="completed",
                company_name=request.company_name,
                lead_research=lead_research,
                company_intelligence=company_intelligence,
                personalization=personalization,
                email_draft=email_draft,
                human_review_required=True,
                review_checklist=review_checklist,
                compliance_notes=[_COMPLIANCE_NOTE, *email_draft.compliance_notes],
                missing_information=self._collect_missing_information(
                    lead_research, company_intelligence, personalization, email_draft
                ),
                confidence_score=self._aggregate_confidence(
                    lead_research, company_intelligence, personalization, email_draft
                ),
                website_research_used=website_research_used,
                website_research=(
                    website_research_result.model_dump(mode="json")
                    if website_research_result is not None
                    else None
                ),
                website_research_warnings=website_research_warnings,
                icp_profile_id=(
                    str(request.icp_profile_id) if request.icp_profile_id else None
                ),
                icp_fit_score=icp_fit_score,
                icp_fit_level=icp_fit_level,
                icp_fit_summary=icp_fit_summary,
                icp_warnings=icp_warnings,
                offer_profile_id=(
                    str(request.offer_profile_id) if request.offer_profile_id else None
                ),
                offer_summary=offer_summary,
                offer_warnings=offer_warnings,
            )

        # Persist the completed run so it can be listed and reviewed later.
        # The saved record's own id replaces the placeholder workflow_id so
        # GET/PATCH .../runs/{workflow_id} can look this run up directly.
        saved_run = await self._history.record_sales_workflow_run(request, response)

        # Sync CRM bookkeeping (Company, Lead, optional Contact, the email
        # draft, and an Interaction/Activity), then link the saved run to
        # the records it produced. This never sends an email, contacts
        # anyone, or books a meeting — it only ever writes CRM records and
        # a draft awaiting human review.
        crm_links = await self._crm_sync.sync(request, response, saved_run.id)
        await self._history.link_crm_entities(
            saved_run.id,
            company_id=crm_links.company_id,
            lead_id=crm_links.lead_id,
            contact_id=crm_links.contact_id,
            email_draft_id=crm_links.email_draft_id,
        )

        workflow_quality_score: int | None = None
        email_draft_quality_score: int | None = None
        quality_warnings: list[str] = []
        if self._quality_scoring is not None and self._settings is not None:
            # Best-effort only: a scoring failure must never fail the
            # workflow itself, and never blocks or changes anything it
            # produced — see QualityScoringService.auto_score.
            if self._settings.quality_auto_score_workflows:
                workflow_score = await self._quality_scoring.auto_score(
                    "workflow_run", saved_run.id
                )
                if workflow_score is not None:
                    workflow_quality_score = workflow_score.score_total
                else:
                    quality_warnings.append("Workflow quality scoring did not complete.")
            if (
                self._settings.quality_auto_score_drafts
                and crm_links.email_draft_id is not None
            ):
                draft_score = await self._quality_scoring.auto_score(
                    "email_draft", crm_links.email_draft_id
                )
                if draft_score is not None:
                    email_draft_quality_score = draft_score.score_total
                else:
                    quality_warnings.append("Email draft quality scoring did not complete.")

        return response.model_copy(
            update={
                "workflow_id": str(saved_run.id),
                "crm_company_id": str(crm_links.company_id),
                "crm_lead_id": str(crm_links.lead_id),
                "crm_email_draft_id": (
                    str(crm_links.email_draft_id)
                    if crm_links.email_draft_id is not None
                    else None
                ),
                "workflow_quality_score": workflow_quality_score,
                "email_draft_quality_score": email_draft_quality_score,
                "quality_warnings": quality_warnings,
            }
        )

    @staticmethod
    def _build_review_checklist(email_draft: EmailDraftResponse) -> list[str]:
        """Build a concrete checklist for the human reviewer."""
        checklist = [
            "Read the lead research, company intelligence, and personalization "
            "output before using the email draft.",
            "Verify every item in the email draft's claims_to_verify before sending.",
            "Confirm none of the email draft's do_not_send_if conditions apply.",
            "Confirm recipient identity, role, and consent to contact.",
            "Obtain explicit human approval before sending the email or making "
            "any contact.",
        ]
        checklist.extend(f"Verify: {claim}" for claim in email_draft.claims_to_verify)
        checklist.extend(
            f"Do not send if: {condition}" for condition in email_draft.do_not_send_if
        )
        return checklist

    @staticmethod
    def _collect_missing_information(
        lead_research: LeadResearchResponse,
        company_intelligence: CompanyIntelligenceResponse,
        personalization: PersonalizationResponse,
        email_draft: EmailDraftResponse,
    ) -> list[str]:
        """Collect missing-information notes from every step, without duplicates."""
        seen: set[str] = set()
        collected: list[str] = []
        for item in (
            lead_research.missing_information
            + company_intelligence.missing_information
            + personalization.missing_information
            + email_draft.missing_information
        ):
            if item not in seen:
                seen.add(item)
                collected.append(item)
        return collected

    @staticmethod
    def _aggregate_confidence(
        lead_research: LeadResearchResponse,
        company_intelligence: CompanyIntelligenceResponse,
        personalization: PersonalizationResponse,
        email_draft: EmailDraftResponse,
    ) -> float:
        """Average the confidence scores of all four steps."""
        scores = [
            lead_research.confidence_score,
            company_intelligence.confidence_score,
            personalization.confidence_score,
            email_draft.confidence_score,
        ]
        return sum(scores) / len(scores)

    @staticmethod
    def _collect_missing_information_partial(
        lead_research: LeadResearchResponse,
        company_intelligence: CompanyIntelligenceResponse,
    ) -> list[str]:
        """Same as :meth:`_collect_missing_information`, for a do-not-contact
        blocked run where only the first two steps ran."""
        seen: set[str] = set()
        collected: list[str] = []
        for item in (
            lead_research.missing_information + company_intelligence.missing_information
        ):
            if item not in seen:
                seen.add(item)
                collected.append(item)
        return collected

    @staticmethod
    def _aggregate_confidence_partial(
        lead_research: LeadResearchResponse,
        company_intelligence: CompanyIntelligenceResponse,
    ) -> float:
        """Same as :meth:`_aggregate_confidence`, for a do-not-contact
        blocked run where only the first two steps ran."""
        scores = [lead_research.confidence_score, company_intelligence.confidence_score]
        return sum(scores) / len(scores)
