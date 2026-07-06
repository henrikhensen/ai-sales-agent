import uuid

from backend.domain.entities.review_event import ReviewEvent
from backend.domain.enums import ReviewEventType
from tests.conftest import FakeReviewEventRepository


async def test_create_persists_event_and_generates_id():
    repo = FakeReviewEventRepository()
    workflow_run_id = uuid.uuid4()

    event = await repo.create(
        ReviewEvent(
            workflow_run_id=workflow_run_id,
            event_type=ReviewEventType.COMMENT_ADDED,
            comment="Bitte prüfen.",
            reviewer_name="Henrik",
        )
    )

    assert event.id is not None
    assert event.created_at is not None
    assert event.workflow_run_id == workflow_run_id
    assert event.comment == "Bitte prüfen."


async def test_list_by_workflow_run_returns_only_matching_events_newest_first():
    repo = FakeReviewEventRepository()
    run_a = uuid.uuid4()
    run_b = uuid.uuid4()

    first = await repo.create(
        ReviewEvent(workflow_run_id=run_a, event_type=ReviewEventType.REVIEW_STARTED)
    )
    second = await repo.create(
        ReviewEvent(workflow_run_id=run_a, event_type=ReviewEventType.APPROVED)
    )
    await repo.create(ReviewEvent(workflow_run_id=run_b, event_type=ReviewEventType.REJECTED))

    events = await repo.list_by_workflow_run(run_a)

    assert {event.id for event in events} == {first.id, second.id}
    assert all(event.workflow_run_id == run_a for event in events)


async def test_list_by_email_draft_returns_only_matching_events():
    repo = FakeReviewEventRepository()
    draft_a = uuid.uuid4()
    draft_b = uuid.uuid4()

    await repo.create(
        ReviewEvent(email_draft_id=draft_a, event_type=ReviewEventType.APPROVED)
    )
    await repo.create(
        ReviewEvent(email_draft_id=draft_b, event_type=ReviewEventType.REJECTED)
    )

    events = await repo.list_by_email_draft(draft_a)

    assert len(events) == 1
    assert events[0].email_draft_id == draft_a


async def test_list_by_workflow_run_returns_empty_for_unknown_run():
    repo = FakeReviewEventRepository()
    events = await repo.list_by_workflow_run(uuid.uuid4())
    assert events == []
