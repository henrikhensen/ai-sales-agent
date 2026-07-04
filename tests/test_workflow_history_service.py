import uuid

import pytest

from backend.application.workflows.history_service import WorkflowHistoryService
from backend.application.workflows.schemas import (
    SalesWorkflowRequest,
    SalesWorkflowResponse,
)
from backend.domain.enums import WorkflowReviewStatus
from backend.domain.exceptions import WorkflowRunNotFoundError
from tests.conftest import FakeWorkflowRunRepository


def _sample_request() -> SalesWorkflowRequest:
    return SalesWorkflowRequest(
        company_name="Acme GmbH", product_or_service_offered="Freight API"
    )


def _sample_response(**overrides) -> SalesWorkflowResponse:
    defaults = dict(
        workflow_id="placeholder",
        status="completed",
        company_name="Acme GmbH",
        lead_research={
            "company_name": "Acme GmbH",
            "short_summary": "A logistics company.",
            "confidence_score": 0.6,
        },
        company_intelligence={
            "company_name": "Acme GmbH",
            "business_summary": "A logistics company.",
            "positioning_summary": "Efficiency-focused carrier.",
            "confidence_score": 0.6,
        },
        personalization={
            "company_name": "Acme GmbH",
            "personalization_summary": "Focus on efficiency gains.",
            "confidence_score": 0.6,
        },
        email_draft={
            "company_name": "Acme GmbH",
            "email_body": "Dear team, ...",
            "confidence_score": 0.6,
        },
        human_review_required=True,
        review_checklist=["Obtain explicit human approval before sending."],
        compliance_notes=["No email was sent, no contact was made."],
        missing_information=["Employee count"],
        confidence_score=0.6,
    )
    defaults.update(overrides)
    return SalesWorkflowResponse(**defaults)


async def test_record_sales_workflow_run_persists_and_returns_run():
    service = WorkflowHistoryService(FakeWorkflowRunRepository())
    request = _sample_request()
    response = _sample_response()

    run = await service.record_sales_workflow_run(request, response)

    assert run.id is not None
    assert run.company_name == "Acme GmbH"
    assert run.workflow_type == "sales"
    assert run.status == "completed"
    assert run.review_status == WorkflowReviewStatus.NEEDS_REVIEW
    assert run.confidence_score == 0.6
    assert run.missing_information == ["Employee count"]
    assert run.compliance_notes == ["No email was sent, no contact was made."]
    assert run.input_payload["company_name"] == "Acme GmbH"
    assert run.result_payload["status"] == "completed"


async def test_get_run_returns_persisted_run():
    service = WorkflowHistoryService(FakeWorkflowRunRepository())
    saved = await service.record_sales_workflow_run(
        _sample_request(), _sample_response()
    )

    fetched = await service.get_run(saved.id)

    assert fetched.id == saved.id
    assert fetched.company_name == "Acme GmbH"


async def test_get_run_raises_for_unknown_id():
    service = WorkflowHistoryService(FakeWorkflowRunRepository())

    with pytest.raises(WorkflowRunNotFoundError):
        await service.get_run(uuid.uuid4())


async def test_list_runs_filters_by_company_name_and_review_status():
    repo = FakeWorkflowRunRepository()
    service = WorkflowHistoryService(repo)
    await service.record_sales_workflow_run(
        _sample_request(), _sample_response(company_name="Acme GmbH")
    )
    other_request = SalesWorkflowRequest(
        company_name="Globex Inc", product_or_service_offered="Widgets"
    )
    saved_globex = await service.record_sales_workflow_run(
        other_request, _sample_response(company_name="Globex Inc")
    )
    await service.update_review_status(saved_globex.id, WorkflowReviewStatus.APPROVED)

    by_name = await service.list_runs(company_name="globex")
    assert len(by_name) == 1
    assert by_name[0].company_name == "Globex Inc"

    by_status = await service.list_runs(review_status=WorkflowReviewStatus.APPROVED)
    assert len(by_status) == 1
    assert by_status[0].company_name == "Globex Inc"

    all_runs = await service.list_runs()
    assert len(all_runs) == 2


async def test_update_review_status_changes_status():
    service = WorkflowHistoryService(FakeWorkflowRunRepository())
    saved = await service.record_sales_workflow_run(
        _sample_request(), _sample_response()
    )
    assert saved.review_status == WorkflowReviewStatus.NEEDS_REVIEW

    updated = await service.update_review_status(
        saved.id, WorkflowReviewStatus.APPROVED
    )

    assert updated.review_status == WorkflowReviewStatus.APPROVED


async def test_update_review_status_raises_for_unknown_id():
    service = WorkflowHistoryService(FakeWorkflowRunRepository())

    with pytest.raises(WorkflowRunNotFoundError):
        await service.update_review_status(uuid.uuid4(), WorkflowReviewStatus.APPROVED)
