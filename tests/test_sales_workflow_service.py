import uuid
from typing import Any

import pytest
from pydantic import ValidationError

from backend.agents.company_intelligence.service import CompanyIntelligenceService
from backend.agents.email_draft.service import EmailDraftService
from backend.agents.lead_research.service import LeadResearchService
from backend.agents.personalization.service import PersonalizationService
from backend.application.workflows.exceptions import WorkflowStepError
from backend.application.workflows.history_service import WorkflowHistoryService
from backend.application.workflows.sales_workflow import SalesWorkflowService
from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)
from backend.infrastructure.llm.base import LLMProvider
from backend.infrastructure.llm.mock_provider import MockLLMProvider
from tests.conftest import FakeWorkflowRunRepository


def _build_service(llm: LLMProvider) -> SalesWorkflowService:
    return SalesWorkflowService(
        lead_research=LeadResearchService(llm),
        company_intelligence=CompanyIntelligenceService(llm),
        personalization=PersonalizationService(llm),
        email_draft=EmailDraftService(llm),
        history=WorkflowHistoryService(FakeWorkflowRunRepository()),
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
    )
    request = SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )

    response = await service.run(request)

    saved = await history.get_run(uuid.UUID(response.workflow_id))
    assert saved.company_name == "Acme GmbH"
    assert saved.status == "completed"
    assert saved.result_payload["status"] == "completed"


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
