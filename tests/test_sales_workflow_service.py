import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from backend.agents.company_intelligence.service import CompanyIntelligenceService
from backend.agents.email_draft.service import EmailDraftService
from backend.agents.lead_research.service import LeadResearchService
from backend.agents.personalization.service import PersonalizationService
from backend.application.research.exceptions import (
    InvalidWebsiteURLError,
    WebsiteFetchFailedError,
)
from backend.application.research.schemas import WebsiteResearchRequest, WebsiteResearchResponse
from backend.application.workflows.exceptions import (
    WebsiteResearchBlockedError,
    WorkflowStepError,
)
from backend.application.compliance.schemas import CreateDoNotContactRequest
from backend.application.crm.workflow_sync_service import WorkflowCrmSyncService
from backend.application.workflows.history_service import WorkflowHistoryService
from backend.application.workflows.sales_workflow import SalesWorkflowService
from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)
from backend.application.sales_strategy.icp_service import ICPService
from backend.application.sales_strategy.offer_service import OfferService
from backend.domain.entities.icp_profile import ICPProfile
from backend.domain.entities.offer_profile import OfferProfile
from backend.domain.enums import PipelineStatus
from backend.domain.exceptions import ICPProfileNotFoundError, OfferProfileNotFoundError
from backend.infrastructure.llm.base import LLMProvider
from backend.infrastructure.llm.mock_provider import MockLLMProvider
from tests.conftest import (
    FakeCompanyRepository,
    FakeContactRepository,
    FakeEmailDraftRepository,
    FakeICPProfileRepository,
    FakeInteractionRepository,
    FakeLeadRepository,
    FakeOfferProfileRepository,
    FakeWorkflowRunRepository,
    build_fake_compliance_service,
    build_fake_crm_sync_service,
    build_fake_icp_service,
    build_fake_offer_service,
)


class _FakeWebsiteResearchService:
    """Test double for WebsiteResearchService: records calls, returns a
    canned result or raises a canned error. Raises AssertionError if called
    while ``allow_calls`` is False, so tests that expect it to be skipped
    fail loudly instead of silently passing.
    """

    def __init__(
        self,
        *,
        result: WebsiteResearchResponse | None = None,
        error: Exception | None = None,
        allow_calls: bool = True,
    ) -> None:
        self._result = result
        self._error = error
        self._allow_calls = allow_calls
        self.calls: list[WebsiteResearchRequest] = []

    async def research(self, request: WebsiteResearchRequest) -> WebsiteResearchResponse:
        if not self._allow_calls:
            raise AssertionError(
                "WebsiteResearchService.research() should not be called when "
                "use_website_research=False"
            )
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        assert self._result is not None
        return self._result


def _unused_website_research_service() -> _FakeWebsiteResearchService:
    return _FakeWebsiteResearchService(allow_calls=False)


def _build_service(
    llm: LLMProvider,
    website_research: _FakeWebsiteResearchService | None = None,
    icp_service=None,
    offer_service=None,
) -> SalesWorkflowService:
    return SalesWorkflowService(
        lead_research=LeadResearchService(llm),
        company_intelligence=CompanyIntelligenceService(llm),
        personalization=PersonalizationService(llm),
        email_draft=EmailDraftService(llm),
        history=WorkflowHistoryService(FakeWorkflowRunRepository()),
        crm_sync=build_fake_crm_sync_service(),
        website_research=website_research or _unused_website_research_service(),
        compliance=build_fake_compliance_service(),
        icp_service=icp_service or build_fake_icp_service(),
        offer_service=offer_service or build_fake_offer_service(),
    )


async def test_workflow_runs_all_steps_with_mock_provider():
    service = _build_service(MockLLMProvider())
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        website_url="https://acme.example.com",
        industry="Logistics",
        product_or_service_offered="Freight visibility platform",
        sender_name="John Smith",
    )

    response = await service.run(request)

    assert isinstance(response, SalesWorkflowResponse)
    assert response.status == "completed"
    assert response.company_name == "Acme GmbH"
    assert response.human_review_required is True
    # Identity fields are grounded in the input across every step.
    assert response.lead_research.company_name == "Acme GmbH"
    assert response.company_intelligence.company_name == "Acme GmbH"
    assert response.personalization.company_name == "Acme GmbH"
    assert response.email_draft.company_name == "Acme GmbH"


async def test_workflow_aggregates_confidence_score():
    service = _build_service(MockLLMProvider())
    request = SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    response = await service.run(request)

    expected = (
        response.lead_research.confidence_score
        + response.company_intelligence.confidence_score
        + response.personalization.confidence_score
        + response.email_draft.confidence_score
    ) / 4
    assert response.confidence_score == pytest.approx(expected)


async def test_workflow_compliance_notes_state_nothing_was_sent():
    service = _build_service(MockLLMProvider())
    request = SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    response = await service.run(request)

    assert any(
        "no email was sent" in note.lower() for note in response.compliance_notes
    )


async def test_workflow_review_checklist_is_populated():
    service = _build_service(MockLLMProvider())
    request = SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    response = await service.run(request)

    assert len(response.review_checklist) > 0
    assert any("approval" in item.lower() for item in response.review_checklist)


async def test_workflow_persists_a_run_and_returns_its_id():
    repo = FakeWorkflowRunRepository()
    history = WorkflowHistoryService(repo)
    llm = MockLLMProvider()
    service = SalesWorkflowService(
        lead_research=LeadResearchService(llm),
        company_intelligence=CompanyIntelligenceService(llm),
        personalization=PersonalizationService(llm),
        email_draft=EmailDraftService(llm),
        history=history,
        crm_sync=build_fake_crm_sync_service(),
        website_research=_unused_website_research_service(),
        compliance=build_fake_compliance_service(),
        icp_service=build_fake_icp_service(),
        offer_service=build_fake_offer_service(),
    )
    request = SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    response = await service.run(request)

    saved = await history.get_run(uuid.UUID(response.workflow_id))
    assert saved.company_name == "Acme GmbH"
    assert saved.status == "completed"
    assert saved.result_payload["status"] == "completed"


async def test_workflow_links_crm_entities_on_the_saved_run():
    repo = FakeWorkflowRunRepository()
    history = WorkflowHistoryService(repo)
    llm = MockLLMProvider()
    service = SalesWorkflowService(
        lead_research=LeadResearchService(llm),
        company_intelligence=CompanyIntelligenceService(llm),
        personalization=PersonalizationService(llm),
        email_draft=EmailDraftService(llm),
        history=history,
        crm_sync=build_fake_crm_sync_service(),
        website_research=_unused_website_research_service(),
        compliance=build_fake_compliance_service(),
        icp_service=build_fake_icp_service(),
        offer_service=build_fake_offer_service(),
    )
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight API",
        recipient_name="Jane Doe",
    )

    response = await service.run(request)

    assert response.crm_company_id is not None
    assert response.crm_lead_id is not None
    assert response.crm_email_draft_id is not None

    saved = await history.get_run(uuid.UUID(response.workflow_id))
    assert str(saved.company_id) == response.crm_company_id
    assert str(saved.lead_id) == response.crm_lead_id
    assert str(saved.email_draft_id) == response.crm_email_draft_id
    assert saved.contact_id is not None


async def test_successful_sales_workflow_sets_lead_pipeline_status_to_draft_created():
    leads = FakeLeadRepository()
    crm_sync = WorkflowCrmSyncService(
        companies=FakeCompanyRepository(),
        leads=leads,
        contacts=FakeContactRepository(),
        interactions=FakeInteractionRepository(),
        email_drafts=FakeEmailDraftRepository(),
    )
    llm = MockLLMProvider()
    service = SalesWorkflowService(
        lead_research=LeadResearchService(llm),
        company_intelligence=CompanyIntelligenceService(llm),
        personalization=PersonalizationService(llm),
        email_draft=EmailDraftService(llm),
        history=WorkflowHistoryService(FakeWorkflowRunRepository()),
        crm_sync=crm_sync,
        website_research=_unused_website_research_service(),
        compliance=build_fake_compliance_service(),
        icp_service=build_fake_icp_service(),
        offer_service=build_fake_offer_service(),
    )
    request = SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    response = await service.run(request)

    lead = await leads.get(uuid.UUID(response.crm_lead_id))
    assert lead.pipeline_status == PipelineStatus.DRAFT_CREATED
    assert lead.pipeline_updated_at is not None


async def test_sales_workflow_blocked_by_do_not_contact_creates_no_email_draft():
    leads = FakeLeadRepository()
    email_drafts = FakeEmailDraftRepository()
    crm_sync = WorkflowCrmSyncService(
        companies=FakeCompanyRepository(),
        leads=leads,
        contacts=FakeContactRepository(),
        interactions=FakeInteractionRepository(),
        email_drafts=email_drafts,
    )
    compliance = build_fake_compliance_service()
    await compliance.create_entry(
        CreateDoNotContactRequest(
            company_name="Blocked GmbH", reason="Legal opt-out request"
        ),
        created_by_user_id=None,
    )
    history = WorkflowHistoryService(FakeWorkflowRunRepository())
    llm = MockLLMProvider()
    service = SalesWorkflowService(
        lead_research=LeadResearchService(llm),
        company_intelligence=CompanyIntelligenceService(llm),
        personalization=PersonalizationService(llm),
        email_draft=EmailDraftService(llm),
        history=history,
        crm_sync=crm_sync,
        website_research=_unused_website_research_service(),
        compliance=compliance,
        icp_service=build_fake_icp_service(),
        offer_service=build_fake_offer_service(),
    )
    request = SalesWorkflowRequest(
        company_name="Blocked GmbH", product_or_service_offered="Freight API"
    )

    response = await service.run(request)

    # Research still ran and completed successfully.
    assert response.status == "blocked"
    assert response.lead_research.company_name == "Blocked GmbH"
    assert response.company_intelligence.company_name == "Blocked GmbH"
    # But outreach preparation stopped here.
    assert response.personalization is None
    assert response.email_draft is None
    assert response.crm_email_draft_id is None
    assert response.do_not_contact_block is not None
    assert response.do_not_contact_block.is_blocked is True
    assert response.do_not_contact_block.matched_by == "company_name"
    assert any(
        "do-not-contact" in note.lower() for note in response.compliance_notes
    )
    assert (await email_drafts.list()) == []

    # Pipeline status never advances to draft_created for a blocked run.
    lead = await leads.get(uuid.UUID(response.crm_lead_id))
    assert lead.pipeline_status == PipelineStatus.NEW

    # Workflow History records that this run was blocked.
    saved = await history.get_run(uuid.UUID(response.workflow_id))
    assert saved.email_draft_id is None
    assert saved.result_payload["do_not_contact_block"]["is_blocked"] is True
    assert saved.result_payload["status"] == "blocked"
    assert any("do-not-contact" in note.lower() for note in saved.compliance_notes)


async def test_workflow_reuses_existing_company_and_lead_across_runs():
    repo = FakeWorkflowRunRepository()
    history = WorkflowHistoryService(repo)
    llm = MockLLMProvider()
    crm_sync = build_fake_crm_sync_service()
    service = SalesWorkflowService(
        lead_research=LeadResearchService(llm),
        company_intelligence=CompanyIntelligenceService(llm),
        personalization=PersonalizationService(llm),
        email_draft=EmailDraftService(llm),
        history=history,
        crm_sync=crm_sync,
        website_research=_unused_website_research_service(),
        compliance=build_fake_compliance_service(),
        icp_service=build_fake_icp_service(),
        offer_service=build_fake_offer_service(),
    )
    request = SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    first = await service.run(request)
    second = await service.run(request)

    assert first.crm_company_id == second.crm_company_id
    assert first.crm_lead_id == second.crm_lead_id
    # Each run still produces its own email draft.
    assert first.crm_email_draft_id != second.crm_email_draft_id


class BrokenEmailDraftLLMProvider(LLMProvider):
    """Returns valid JSON for the first three schemas, invalid for the fourth.

    Distinguishes steps by prompt content, since all four steps share the
    same provider interface.
    """

    name = "broken-email-draft"

    async def generate_json(
        self,
        *,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        if "Draft a single sales email" in prompt:
            return {"confidence_score": "not-a-number"}
        return await MockLLMProvider().generate_json(
            system=system, prompt=prompt, schema=schema, max_tokens=max_tokens
        )


async def test_workflow_raises_step_error_on_invalid_output():
    service = _build_service(BrokenEmailDraftLLMProvider())
    request = SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    with pytest.raises(WorkflowStepError) as exc_info:
        await service.run(request)

    assert exc_info.value.step == "email_draft"


async def test_workflow_rejects_invalid_tone_before_email_draft_step():
    # The Literal-typed `tone` field on SalesWorkflowRequest already rejects
    # invalid values at the API boundary, so an invalid tone can never reach
    # the email_draft step in practice — this documents that contract.
    with pytest.raises(ValidationError):
        SalesWorkflowRequest(
            company_name="Acme GmbH",
            product_or_service_offered="Freight API",
            tone="aggressive",
        )


# -- Website Research integration (Phase 18C.2) ------------------------------

def _website_research_result(
    extracted_text: str = "Acme builds freight visibility software for logistics companies.",
    warnings: list[str] | None = None,
) -> WebsiteResearchResponse:
    return WebsiteResearchResponse(
        url="https://acme.example.com",
        final_url="https://acme.example.com",
        domain="acme.example.com",
        title="Acme GmbH",
        meta_description=None,
        extracted_text=extracted_text,
        text_length=len(extracted_text),
        pages_fetched=1,
        sources_used=["https://acme.example.com"],
        warnings=warnings or [],
    )


async def test_website_research_is_called_when_requested():
    website_research = _FakeWebsiteResearchService(result=_website_research_result())
    service = _build_service(MockLLMProvider(), website_research=website_research)
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight API",
        website_url="https://acme.example.com",
        use_website_research=True,
    )

    response = await service.run(request)

    assert len(website_research.calls) == 1
    assert website_research.calls[0].url == "https://acme.example.com/"
    assert website_research.calls[0].include_same_domain_links is False
    assert response.website_research_used is True
    assert response.website_research is not None
    assert response.website_research["domain"] == "acme.example.com"


async def test_website_research_is_not_called_when_not_requested():
    website_research = _unused_website_research_service()
    service = _build_service(MockLLMProvider(), website_research=website_research)
    request = SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    response = await service.run(request)

    assert website_research.calls == []
    assert response.website_research_used is False
    assert response.website_research is None
    assert response.website_research_warnings == []


async def test_extracted_text_is_used_for_company_intelligence_when_website_text_missing():
    extracted_text = "Acme builds freight visibility software for logistics companies."
    website_research = _FakeWebsiteResearchService(
        result=_website_research_result(extracted_text=extracted_text)
    )
    service = _build_service(MockLLMProvider(), website_research=website_research)
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight API",
        website_url="https://acme.example.com",
        use_website_research=True,
    )

    response = await service.run(request)

    # The mock provider echoes the full prompt into string output fields, so
    # the extracted text appearing there proves it reached the prompt.
    assert extracted_text in response.company_intelligence.business_summary


async def test_explicit_website_text_wins_over_extracted_text():
    website_research = _FakeWebsiteResearchService(
        result=_website_research_result(extracted_text="Text from the fetched page.")
    )
    service = _build_service(MockLLMProvider(), website_research=website_research)
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight API",
        website_url="https://acme.example.com",
        website_text="User-supplied website text.",
        use_website_research=True,
    )

    response = await service.run(request)

    assert "User-supplied website text." in response.company_intelligence.business_summary
    assert "Text from the fetched page." not in response.company_intelligence.business_summary


async def test_website_research_warnings_are_included_in_response():
    website_research = _FakeWebsiteResearchService(
        result=_website_research_result(
            warnings=["Extracted text was truncated to 20000 characters."]
        )
    )
    service = _build_service(MockLLMProvider(), website_research=website_research)
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight API",
        website_url="https://acme.example.com",
        use_website_research=True,
    )

    response = await service.run(request)

    assert "Extracted text was truncated to 20000 characters." in (
        response.website_research_warnings
    )


async def test_workflow_continues_when_website_research_fetch_fails():
    website_research = _FakeWebsiteResearchService(
        error=WebsiteFetchFailedError("Timed out fetching the page.")
    )
    service = _build_service(MockLLMProvider(), website_research=website_research)
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight API",
        website_url="https://acme.example.com",
        use_website_research=True,
    )

    response = await service.run(request)

    assert response.status == "completed"
    assert response.website_research_used is False
    assert response.website_research is None
    assert any(
        "Timed out fetching the page." in warning
        for warning in response.website_research_warnings
    )


async def test_workflow_aborts_when_website_research_url_is_blocked():
    website_research = _FakeWebsiteResearchService(
        error=InvalidWebsiteURLError("Host is not allowed.")
    )
    service = _build_service(MockLLMProvider(), website_research=website_research)
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight API",
        website_url="https://acme.example.com",
        use_website_research=True,
    )

    with pytest.raises(WebsiteResearchBlockedError) as exc_info:
        await service.run(request)

    assert "Host is not allowed." in exc_info.value.reason


async def test_workflow_run_persists_website_research_fields():
    repo = FakeWorkflowRunRepository()
    history = WorkflowHistoryService(repo)
    website_research = _FakeWebsiteResearchService(
        result=_website_research_result(warnings=["Extracted text was truncated."])
    )
    service = SalesWorkflowService(
        lead_research=LeadResearchService(MockLLMProvider()),
        company_intelligence=CompanyIntelligenceService(MockLLMProvider()),
        personalization=PersonalizationService(MockLLMProvider()),
        email_draft=EmailDraftService(MockLLMProvider()),
        history=history,
        crm_sync=build_fake_crm_sync_service(),
        website_research=website_research,
        compliance=build_fake_compliance_service(),
        icp_service=build_fake_icp_service(),
        offer_service=build_fake_offer_service(),
    )
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight API",
        website_url="https://acme.example.com",
        use_website_research=True,
        website_research_max_pages=2,
    )

    response = await service.run(request)

    saved = await history.get_run(uuid.UUID(response.workflow_id))
    assert saved.input_payload["use_website_research"] is True
    assert saved.input_payload["website_research_max_pages"] == 2
    assert saved.result_payload["website_research_used"] is True
    assert saved.result_payload["website_research"]["domain"] == "acme.example.com"
    assert saved.result_payload["website_research_warnings"] == [
        "Extracted text was truncated."
    ]


async def test_workflow_without_website_research_still_works():
    service = _build_service(MockLLMProvider())
    request = SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    response = await service.run(request)

    assert response.status == "completed"
    assert response.website_research_used is False
    assert response.website_research is None
    assert response.website_research_warnings == []


# -- ICP / Offer integration ---------------------------------------------------


async def test_sales_workflow_funktioniert_ohne_icp_und_offer():
    service = _build_service(MockLLMProvider())
    request = SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    response = await service.run(request)

    assert response.status == "completed"
    assert response.icp_profile_id is None
    assert response.icp_fit_score is None
    assert response.offer_profile_id is None
    assert response.offer_summary is None


async def test_sales_workflow_funktioniert_mit_icp():
    icp_repo = FakeICPProfileRepository()
    icp = await icp_repo.create(
        ICPProfile(
            name="Logistics ICP",
            target_industries=["Logistics"],
            minimum_fit_score=70,
        )
    )
    service = _build_service(MockLLMProvider(), icp_service=build_fake_icp_service(icp_repo))
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        industry="Logistics",
        product_or_service_offered="Freight API",
        icp_profile_id=icp.id,
    )

    response = await service.run(request)

    assert response.status == "completed"
    assert response.icp_profile_id == str(icp.id)
    assert response.icp_fit_score is not None
    assert response.icp_fit_level is not None
    assert response.icp_fit_summary is not None


async def test_sales_workflow_funktioniert_mit_offer():
    offer_repo = FakeOfferProfileRepository()
    offer = await offer_repo.create(
        OfferProfile(
            name="Fleet Suite",
            main_value_proposition="Real-time fleet visibility for logistics teams.",
            key_benefits=["Fewer missed deliveries"],
        )
    )
    service = _build_service(
        MockLLMProvider(), offer_service=build_fake_offer_service(offer_repo)
    )
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight API",
        offer_profile_id=offer.id,
    )

    response = await service.run(request)

    assert response.status == "completed"
    assert response.offer_profile_id == str(offer.id)
    assert response.offer_summary is not None
    assert "Real-time fleet visibility" in response.offer_summary


async def test_email_draft_nutzt_offer_kontext():
    offer_repo = FakeOfferProfileRepository()
    offer = await offer_repo.create(
        OfferProfile(
            name="Fleet Suite",
            main_value_proposition="UNIQUE_VALUE_PROP_MARKER for fleet visibility",
            call_to_action="Book a 15-minute demo",
        )
    )
    service = _build_service(
        MockLLMProvider(), offer_service=build_fake_offer_service(offer_repo)
    )
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight API",
        offer_profile_id=offer.id,
    )

    response = await service.run(request)

    # The mock LLM echoes the full rendered prompt into every free-text
    # output field, so the offer's value proposition — injected into the
    # combined notes passed to both Personalization and Email Draft — must
    # show up in the final draft body.
    assert "UNIQUE_VALUE_PROP_MARKER" in response.email_draft.email_body


async def test_sales_workflow_speichert_icp_und_offer_in_history():
    icp_repo = FakeICPProfileRepository()
    icp = await icp_repo.create(
        ICPProfile(name="Logistics ICP", target_industries=["Logistics"])
    )
    offer_repo = FakeOfferProfileRepository()
    offer = await offer_repo.create(
        OfferProfile(
            name="Fleet Suite", main_value_proposition="Real-time fleet visibility."
        )
    )
    repo = FakeWorkflowRunRepository()
    history = WorkflowHistoryService(repo)
    llm = MockLLMProvider()
    service = SalesWorkflowService(
        lead_research=LeadResearchService(llm),
        company_intelligence=CompanyIntelligenceService(llm),
        personalization=PersonalizationService(llm),
        email_draft=EmailDraftService(llm),
        history=history,
        crm_sync=build_fake_crm_sync_service(),
        website_research=_unused_website_research_service(),
        compliance=build_fake_compliance_service(),
        icp_service=build_fake_icp_service(icp_repo),
        offer_service=build_fake_offer_service(offer_repo),
    )
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        industry="Logistics",
        product_or_service_offered="Freight API",
        icp_profile_id=icp.id,
        offer_profile_id=offer.id,
    )

    response = await service.run(request)

    saved = await history.get_run(uuid.UUID(response.workflow_id))
    assert saved.result_payload["icp_profile_id"] == str(icp.id)
    assert saved.result_payload["icp_fit_score"] is not None
    assert saved.result_payload["offer_profile_id"] == str(offer.id)
    assert saved.result_payload["offer_summary"] is not None
    assert saved.input_payload["icp_profile_id"] == str(icp.id)
    assert saved.input_payload["offer_profile_id"] == str(offer.id)


async def test_sales_workflow_raises_for_unknown_icp_profile_id():
    service = _build_service(MockLLMProvider())
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight API",
        icp_profile_id=uuid.uuid4(),
    )

    with pytest.raises(ICPProfileNotFoundError):
        await service.run(request)


async def test_sales_workflow_raises_for_unknown_offer_profile_id():
    service = _build_service(MockLLMProvider())
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        product_or_service_offered="Freight API",
        offer_profile_id=uuid.uuid4(),
    )

    with pytest.raises(OfferProfileNotFoundError):
        await service.run(request)


async def test_weak_icp_fit_adds_a_review_checklist_warning():
    icp_repo = FakeICPProfileRepository()
    icp = await icp_repo.create(
        ICPProfile(
            name="Strict ICP",
            excluded_industries=["Gambling"],
            minimum_fit_score=70,
        )
    )
    service = _build_service(MockLLMProvider(), icp_service=build_fake_icp_service(icp_repo))
    request = SalesWorkflowRequest(
        company_name="Acme GmbH",
        industry="Gambling",
        product_or_service_offered="Freight API",
        icp_profile_id=icp.id,
    )

    response = await service.run(request)

    assert response.icp_fit_level in ("weak", "not_fit")
    assert any("ICP fit" in item for item in response.review_checklist)
