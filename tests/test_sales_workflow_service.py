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
from backend.application.workflows.exceptions import WorkflowStepError
from backend.application.workflows.history_service import WorkflowHistoryService
from backend.application.workflows.sales_workflow import SalesWorkflowService
from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)
from backend.infrastructure.llm.base import LLMProvider
from backend.infrastructure.llm.mock_provider import MockLLMProvider
from tests.conftest import FakeWorkflowRunRepository, build_fake_crm_sync_service


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
    llm: LLMProvider, website_research: _FakeWebsiteResearchService | None = None
) -> SalesWorkflowService:
    return SalesWorkflowService(
        lead_research=LeadResearchService(llm),
        company_intelligence=CompanyIntelligenceService(llm),
        personalization=PersonalizationService(llm),
        email_draft=EmailDraftService(llm),
        history=WorkflowHistoryService(FakeWorkflowRunRepository()),
        crm_sync=build_fake_crm_sync_service(),
        website_research=website_research or _unused_website_research_service(),
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

    with pytest.raises(WorkflowStepError) as exc_info:
        await service.run(request)

    assert exc_info.value.step == "website_research"


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
