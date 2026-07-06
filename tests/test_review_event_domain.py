import uuid
from datetime import datetime, timezone

from backend.domain.entities.review_event import ReviewEvent
from backend.domain.enums import ReviewEventType
from backend.infrastructure.database.models.review_event import ReviewEventModel
from backend.infrastructure.repositories.review_event import (
    SQLAlchemyReviewEventRepository,
)


def test_review_event_defaults():
    event = ReviewEvent(event_type=ReviewEventType.APPROVED)

    assert event.workflow_run_id is None
    assert event.email_draft_id is None
    assert event.previous_status is None
    assert event.new_status is None
    assert event.comment is None
    assert event.reviewer_name is None
    assert event.metadata is None
    assert event.id is None


def test_review_event_type_has_seven_allowed_values():
    values = {event_type.value for event_type in ReviewEventType}
    assert values == {
        "review_started",
        "comment_added",
        "approved",
        "rejected",
        "changes_requested",
        "archived",
        "blocked",
    }


def test_approved_event_is_not_a_send_flag():
    # Documents the contract explicitly: "approved" is an internal marker,
    # never a send/outreach trigger.
    event = ReviewEvent(event_type=ReviewEventType.APPROVED, new_status="approved")
    assert not hasattr(event, "sent")
    assert not hasattr(event, "contacted")
    assert not hasattr(event, "email_sent")


def test_repository_maps_orm_row_to_domain_entity():
    now = datetime.now(timezone.utc)
    orm_obj = ReviewEventModel(
        id=uuid.uuid4(),
        workflow_run_id=uuid.uuid4(),
        email_draft_id=uuid.uuid4(),
        event_type=ReviewEventType.APPROVED,
        previous_status="needs_review",
        new_status="approved",
        comment="Sieht gut aus.",
        reviewer_name="Henrik",
        event_metadata={"source": "manual"},
        created_at=now,
    )

    entity = SQLAlchemyReviewEventRepository._to_entity(orm_obj)

    assert isinstance(entity, ReviewEvent)
    assert entity.id == orm_obj.id
    assert entity.workflow_run_id == orm_obj.workflow_run_id
    assert entity.email_draft_id == orm_obj.email_draft_id
    assert entity.event_type == ReviewEventType.APPROVED
    assert entity.previous_status == "needs_review"
    assert entity.new_status == "approved"
    assert entity.comment == "Sieht gut aus."
    assert entity.reviewer_name == "Henrik"
    assert entity.metadata == {"source": "manual"}
    assert entity.created_at == now
