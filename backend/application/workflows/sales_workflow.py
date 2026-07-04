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
from backend.application.workflows.exceptions import WorkflowStepError
from backend.application.workflows.history_service import WorkflowHistoryService
from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)

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
    ) -> None:
        self._lead_research = lead_research
        self._company_intelligence = company_intelligence
        self._personalization = personalization
        self._email_draft = email_draft
        self._history = history

    async def run(self, request: SalesWorkflowRequest) -> SalesWorkflowResponse:
        """Execute all four steps and return a human-review summary.

        Raises:
            WorkflowStepError: if any step's output fails validation (e.g. the
                configured LLM provider returned malformed JSON).
        """
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

        try:
            company_intelligence = await self._company_intelligence.analyze(
                CompanyIntelligenceRequest(
                    company_name=request.company_name,
                    website_url=request.website_url,
                    industry=request.industry,
                    location=request.location,
                    company_description=request.company_description,
                    website_text=request.website_text,
                    notes=request.notes,
                )
            )
        except InvalidCompanyIntelligenceOutputError as exc:
            raise WorkflowStepError("company_intelligence", exc.reason) from exc

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
                    known_pain_points=lead_research.likely_pain_points,
                    notes=request.notes,
                )
            )
        except InvalidPersonalizationOutputError as exc:
            raise WorkflowStepError("personalization", exc.reason) from exc

        try:
            email_draft_request = EmailDraftRequest(
                company_name=request.company_name,
                website_url=request.website_url,
                industry=request.industry,
                recipient_role=request.target_persona,
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
                notes=request.notes,
            )
        except ValidationError as exc:
            raise WorkflowStepError("email_draft", str(exc)) from exc

        try:
            email_draft = await self._email_draft.draft(email_draft_request)
        except InvalidEmailDraftOutputError as exc:
            raise WorkflowStepError("email_draft", exc.reason) from exc

        response = SalesWorkflowResponse(
            workflow_id=str(uuid.uuid4()),
            status="completed",
            company_name=request.company_name,
            lead_research=lead_research,
            company_intelligence=company_intelligence,
            personalization=personalization,
            email_draft=email_draft,
            human_review_required=True,
            review_checklist=self._build_review_checklist(email_draft),
            compliance_notes=[_COMPLIANCE_NOTE, *email_draft.compliance_notes],
            missing_information=self._collect_missing_information(
                lead_research, company_intelligence, personalization, email_draft
            ),
            confidence_score=self._aggregate_confidence(
                lead_research, company_intelligence, personalization, email_draft
            ),
        )

        # Persist the completed run so it can be listed and reviewed later.
        # The saved record's own id replaces the placeholder workflow_id so
        # GET/PATCH .../runs/{workflow_id} can look this run up directly.
        saved_run = await self._history.record_sales_workflow_run(request, response)
        return response.model_copy(update={"workflow_id": str(saved_run.id)})

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
