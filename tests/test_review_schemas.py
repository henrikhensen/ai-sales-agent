from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.api.v1.schemas.review import (
    EmailDraftReviewStatusResponse,
    EmailDraftReviewStatusUpdateRequest,
    ReviewEventListResponse,
    ReviewEventResponse,
    WorkflowCommentRequest,
    WorkflowCommentResponse,
)
from backend.domain.enums import EmailDraftReviewStatus, ReviewEventType


# -- EmailDraftReviewStatusUpdateRequest -------------------------------------

def test_email_draft_review_status_request_accepts_minimal_input():
    request = EmailDraftReviewStatusUpdateRequest(review_status="approved")
    assert request.review_status == EmailDraftReviewStatus.APPROVED
    assert request.reviewer_name is None
    assert request.comment is None


def test_email_draft_review_status_request_accepts_full_input():
    request = EmailDraftReviewStatusUpdateRequest(
        review_status="approved",
        reviewer_name="Henrik",
        comment="Entwurf geprüft, aber noch nicht senden.",
    )
    assert request.reviewer_name == "Henrik"
    assert request.comment == "Entwurf geprüft, aber noch nicht senden."


@pytest.mark.parametrize(
    "value",
    ["needs_review", "in_review", "approved", "rejected", "changes_requested", "archived"],
)
def test_email_draft_review_status_request_accepts_all_allowed_values(value):
    request = EmailDraftReviewStatusUpdateRequest(review_status=value)
    assert request.review_status.value == value


def test_email_draft_review_status_request_rejects_unknown_value():
    with pytest.raises(ValidationError):
        EmailDraftReviewStatusUpdateRequest(review_status="sent")


def test_email_draft_review_status_request_rejects_whitespace_only_comment():
    with pytest.raises(ValidationError):
        EmailDraftReviewStatusUpdateRequest(review_status="approved", comment="   ")


def test_email_draft_review_status_request_rejects_whitespace_only_reviewer_name():
    with pytest.raises(ValidationError):
        EmailDraftReviewStatusUpdateRequest(review_status="approved", reviewer_name="   ")


def test_email_draft_review_status_request_rejects_comment_over_max_length():
    with pytest.raises(ValidationError):
        EmailDraftReviewStatusUpdateRequest(review_status="approved", comment="x" * 2001)


def test_email_draft_review_status_request_trims_fields():
    request = EmailDraftReviewStatusUpdateRequest(
        review_status="approved", reviewer_name="  Henrik  ", comment="  Sieht gut aus.  "
    )
    assert request.reviewer_name == "Henrik"
    assert request.comment == "Sieht gut aus."


# -- EmailDraftReviewStatusResponse ------------------------------------------

def test_email_draft_review_status_response_states_nothing_was_sent():
    response = EmailDraftReviewStatusResponse(
        email_draft_id=uuid4(),
        review_status="approved",
        reviewer_name="Henrik",
        review_comment="ok",
        reviewed_at=datetime.now(timezone.utc),
    )
    assert "keine e-mail gesendet" in response.message.lower()
    assert not hasattr(response, "sent")


# -- WorkflowCommentRequest ---------------------------------------------------

def test_workflow_comment_request_requires_comment():
    with pytest.raises(ValidationError):
        WorkflowCommentRequest(reviewer_name="Henrik")


def test_workflow_comment_request_rejects_whitespace_only_comment():
    with pytest.raises(ValidationError):
        WorkflowCommentRequest(comment="   ")


def test_workflow_comment_request_rejects_comment_over_max_length():
    with pytest.raises(ValidationError):
        WorkflowCommentRequest(comment="x" * 2001)


def test_workflow_comment_request_accepts_valid_input():
    request = WorkflowCommentRequest(reviewer_name="Henrik", comment="Bitte prüfen.")
    assert request.reviewer_name == "Henrik"
    assert request.comment == "Bitte prüfen."


def test_workflow_comment_response_states_nothing_was_sent():
    response = WorkflowCommentResponse(workflow_id=uuid4(), event_id=uuid4())
    assert "keine e-mail gesendet" in response.message.lower()


# -- ReviewEventResponse ------------------------------------------------------

def test_review_event_response_accepts_valid_payload():
    event = ReviewEventResponse(
        id=uuid4(),
        workflow_run_id=uuid4(),
        email_draft_id=None,
        event_type="approved",
        previous_status="needs_review",
        new_status="approved",
        comment="ok",
        reviewer_name="Henrik",
        metadata=None,
        created_at=datetime.now(timezone.utc),
    )
    assert event.event_type == ReviewEventType.APPROVED


def test_review_event_response_rejects_unknown_event_type():
    with pytest.raises(ValidationError):
        ReviewEventResponse(
            id=uuid4(),
            workflow_run_id=uuid4(),
            email_draft_id=None,
            event_type="sent",
            previous_status=None,
            new_status=None,
            comment=None,
            reviewer_name=None,
            metadata=None,
            created_at=datetime.now(timezone.utc),
        )


def test_review_event_list_response_wraps_events():
    event = ReviewEventResponse(
        id=uuid4(),
        workflow_run_id=None,
        email_draft_id=uuid4(),
        event_type="comment_added",
        previous_status=None,
        new_status=None,
        comment="Bitte prüfen.",
        reviewer_name=None,
        metadata=None,
        created_at=datetime.now(timezone.utc),
    )
    listing = ReviewEventListResponse(items=[event])
    assert len(listing.items) == 1
