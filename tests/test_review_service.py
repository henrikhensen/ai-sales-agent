import uuid

import pytest

from backend.application.reviews.review_service import ReviewService
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.entities.workflow_run import WorkflowRun
from backend.domain.enums import EmailDraftReviewStatus, ReviewEventType, WorkflowReviewStatus
from backend.domain.exceptions import EmailDraftNotFoundError, WorkflowRunNotFoundError
from tests.conftest import (
    FakeEmailDraftRepository,
    FakeReviewEventRepository,
    FakeWorkflowRunRepository,
)


def _build_service():
    email_drafts = FakeEmailDraftRepository()
    workflow_runs = FakeWorkflowRunRepository()
    review_events = FakeReviewEventRepository()
    service = ReviewService(
        email_drafts=email_drafts, workflow_runs=workflow_runs, review_events=review_events
    )
    return service, email_drafts, workflow_runs, review_events


async def _create_draft(email_drafts: FakeEmailDraftRepository, **overrides) -> EmailDraft:
    defaults = dict(company_id=uuid.uuid4(), email_body="Hallo,\n\nGrüße")
    defaults.update(overrides)
    return await email_drafts.create(EmailDraft(**defaults))


async def _create_workflow_run(workflow_runs: FakeWorkflowRunRepository) -> WorkflowRun:
    return await workflow_runs.create(
        WorkflowRun(
            company_name="Acme GmbH",
            status="completed",
            input_payload={},
            result_payload={},
        )
    )


# -- approve / reject email draft --------------------------------------------

async def test_approve_email_draft_sets_review_status_and_reviewer():
    service, email_drafts, _workflow_runs, _events = _build_service()
    draft = await _create_draft(email_drafts)

    updated = await service.set_email_draft_review_status(
        draft.id,
        review_status=EmailDraftReviewStatus.APPROVED,
        reviewer_name="Henrik",
        comment="Entwurf geprüft, aber noch nicht senden.",
    )

    assert updated.review_status == EmailDraftReviewStatus.APPROVED
    assert updated.reviewer_name == "Henrik"
    assert updated.review_comment == "Entwurf geprüft, aber noch nicht senden."
    assert updated.reviewed_at is not None
    # Approval never sets anything resembling a "sent" flag.
    assert not hasattr(updated, "sent")
    assert not hasattr(updated, "sent_at")


async def test_approve_email_draft_writes_audit_event():
    service, email_drafts, _workflow_runs, events = _build_service()
    draft = await _create_draft(email_drafts)

    await service.set_email_draft_review_status(
        draft.id, review_status=EmailDraftReviewStatus.APPROVED, reviewer_name="Henrik", comment=None
    )

    trail = await events.list_by_email_draft(draft.id)
    assert len(trail) == 1
    assert trail[0].event_type == ReviewEventType.APPROVED
    assert trail[0].previous_status == "needs_review"
    assert trail[0].new_status == "approved"
    assert trail[0].reviewer_name == "Henrik"


async def test_reject_email_draft_sets_review_status_and_writes_event():
    service, email_drafts, _workflow_runs, events = _build_service()
    draft = await _create_draft(email_drafts)

    updated = await service.set_email_draft_review_status(
        draft.id,
        review_status=EmailDraftReviewStatus.REJECTED,
        reviewer_name="Henrik",
        comment="Passt nicht.",
    )

    assert updated.review_status == EmailDraftReviewStatus.REJECTED
    trail = await events.list_by_email_draft(draft.id)
    assert trail[0].event_type == ReviewEventType.REJECTED
    assert trail[0].comment == "Passt nicht."


async def test_changes_requested_email_draft_writes_matching_event():
    service, email_drafts, _workflow_runs, events = _build_service()
    draft = await _create_draft(email_drafts)

    await service.set_email_draft_review_status(
        draft.id,
        review_status=EmailDraftReviewStatus.CHANGES_REQUESTED,
        reviewer_name="Henrik",
        comment="Bitte Nutzenargument prüfen.",
    )

    trail = await events.list_by_email_draft(draft.id)
    assert trail[0].event_type == ReviewEventType.CHANGES_REQUESTED


async def test_set_email_draft_review_status_raises_for_unknown_draft():
    service, _email_drafts, _workflow_runs, _events = _build_service()

    with pytest.raises(EmailDraftNotFoundError):
        await service.set_email_draft_review_status(
            uuid.uuid4(), review_status=EmailDraftReviewStatus.APPROVED, reviewer_name=None, comment=None
        )


async def test_approving_a_draft_never_sends_anything():
    # Documents the contract: nothing about approval implies sending.
    service, email_drafts, _workflow_runs, _events = _build_service()
    draft = await _create_draft(email_drafts)

    updated = await service.set_email_draft_review_status(
        draft.id, review_status=EmailDraftReviewStatus.APPROVED, reviewer_name="Henrik", comment=None
    )

    assert updated.status == "draft"


# -- linked workflow run review status ---------------------------------------

async def test_approving_linked_draft_updates_workflow_run_review_status():
    service, email_drafts, workflow_runs, _events = _build_service()
    run = await _create_workflow_run(workflow_runs)
    draft = await _create_draft(email_drafts, workflow_run_id=run.id)

    await service.set_email_draft_review_status(
        draft.id, review_status=EmailDraftReviewStatus.APPROVED, reviewer_name="Henrik", comment=None
    )

    updated_run = await workflow_runs.get_by_id(run.id)
    assert updated_run.review_status == WorkflowReviewStatus.APPROVED


async def test_rejecting_linked_draft_updates_workflow_run_review_status():
    service, email_drafts, workflow_runs, _events = _build_service()
    run = await _create_workflow_run(workflow_runs)
    draft = await _create_draft(email_drafts, workflow_run_id=run.id)

    await service.set_email_draft_review_status(
        draft.id, review_status=EmailDraftReviewStatus.REJECTED, reviewer_name="Henrik", comment=None
    )

    updated_run = await workflow_runs.get_by_id(run.id)
    assert updated_run.review_status == WorkflowReviewStatus.REJECTED


async def test_draft_without_workflow_run_does_not_touch_any_run():
    service, email_drafts, workflow_runs, _events = _build_service()
    run = await _create_workflow_run(workflow_runs)
    draft = await _create_draft(email_drafts)  # no workflow_run_id

    await service.set_email_draft_review_status(
        draft.id, review_status=EmailDraftReviewStatus.APPROVED, reviewer_name="Henrik", comment=None
    )

    unrelated_run = await workflow_runs.get_by_id(run.id)
    assert unrelated_run.review_status == WorkflowReviewStatus.NEEDS_REVIEW


# -- list email draft events --------------------------------------------------

async def test_list_email_draft_events_raises_for_unknown_draft():
    service, _email_drafts, _workflow_runs, _events = _build_service()

    with pytest.raises(EmailDraftNotFoundError):
        await service.list_email_draft_events(uuid.uuid4())


# -- workflow comments ---------------------------------------------------------

async def test_add_workflow_comment_writes_comment_added_event():
    service, _email_drafts, workflow_runs, events = _build_service()
    run = await _create_workflow_run(workflow_runs)

    event = await service.add_workflow_comment(
        run.id, reviewer_name="Henrik", comment="Bitte Nutzenargument prüfen."
    )

    assert event.event_type == ReviewEventType.COMMENT_ADDED
    assert event.comment == "Bitte Nutzenargument prüfen."
    assert event.workflow_run_id == run.id

    trail = await events.list_by_workflow_run(run.id)
    assert len(trail) == 1
    assert trail[0].id == event.id


async def test_add_workflow_comment_does_not_change_review_status():
    service, _email_drafts, workflow_runs, _events = _build_service()
    run = await _create_workflow_run(workflow_runs)

    await service.add_workflow_comment(run.id, reviewer_name="Henrik", comment="Bitte prüfen.")

    unchanged_run = await workflow_runs.get_by_id(run.id)
    assert unchanged_run.review_status == WorkflowReviewStatus.NEEDS_REVIEW


async def test_add_workflow_comment_raises_for_unknown_workflow_run():
    service, _email_drafts, _workflow_runs, _events = _build_service()

    with pytest.raises(WorkflowRunNotFoundError):
        await service.add_workflow_comment(uuid.uuid4(), reviewer_name="Henrik", comment="Hallo")


async def test_list_workflow_events_raises_for_unknown_workflow_run():
    service, _email_drafts, _workflow_runs, _events = _build_service()

    with pytest.raises(WorkflowRunNotFoundError):
        await service.list_workflow_events(uuid.uuid4())
