from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.api.v1.schemas.workflow_run import (
    UpdateWorkflowReviewStatusRequest,
    UpdateWorkflowReviewStatusResponse,
    WorkflowRunDetail,
    WorkflowRunListResponse,
    WorkflowRunSummary,
)
from backend.domain.enums import WorkflowReviewStatus


def _summary_kwargs() -> dict:
    now = datetime.now(timezone.utc)
    return {
        "id": uuid4(),
        "company_name": "Acme GmbH",
        "workflow_type": "sales",
        "status": "completed",
        "review_status": WorkflowReviewStatus.NEEDS_REVIEW,
        "confidence_score": 0.6,
        "created_at": now,
        "updated_at": now,
    }


def test_workflow_run_summary_accepts_valid_payload():
    summary = WorkflowRunSummary(**_summary_kwargs())
    assert summary.company_name == "Acme GmbH"
    assert summary.review_status == WorkflowReviewStatus.NEEDS_REVIEW


def test_workflow_run_summary_rejects_invalid_review_status():
    with pytest.raises(ValidationError):
        WorkflowRunSummary(**{**_summary_kwargs(), "review_status": "sent"})


def test_workflow_run_detail_requires_payload_fields():
    with pytest.raises(ValidationError):
        WorkflowRunDetail(**_summary_kwargs())


def test_workflow_run_detail_accepts_valid_payload():
    detail = WorkflowRunDetail(
        **_summary_kwargs(),
        input_payload={"company_name": "Acme GmbH"},
        result_payload={"status": "completed"},
        missing_information=["Employee count"],
        compliance_notes=["No email was sent."],
    )
    assert detail.input_payload["company_name"] == "Acme GmbH"
    assert detail.missing_information == ["Employee count"]


def test_workflow_run_list_response_wraps_summaries():
    listing = WorkflowRunListResponse(
        items=[WorkflowRunSummary(**_summary_kwargs())], limit=100, offset=0
    )
    assert len(listing.items) == 1
    assert listing.limit == 100
    assert listing.offset == 0


def test_update_review_status_request_accepts_all_allowed_values():
    for value in ("needs_review", "reviewed", "approved", "rejected", "archived"):
        request = UpdateWorkflowReviewStatusRequest(review_status=value)
        assert request.review_status.value == value


def test_update_review_status_request_rejects_unknown_value():
    with pytest.raises(ValidationError):
        UpdateWorkflowReviewStatusRequest(review_status="sent")


def test_update_review_status_response_is_a_full_detail_view():
    response = UpdateWorkflowReviewStatusResponse(
        **_summary_kwargs(),
        input_payload={},
        result_payload={},
        missing_information=[],
        compliance_notes=[],
    )
    assert response.company_name == "Acme GmbH"
