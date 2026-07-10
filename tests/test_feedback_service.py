"""Tests for FeedbackService using the in-memory FakeUserFeedbackRepository —
no real database, no automatic action of any kind triggered by feedback.
"""

import uuid

import pytest

from backend.application.quality.feedback_schemas import (
    CreateQualityFeedbackRequest,
    ReviewQualityFeedbackRequest,
)
from backend.domain.exceptions import UserFeedbackNotFoundError
from tests.conftest import build_fake_feedback_service


async def test_create_feedback_stores_it_and_defaults_review_status_open():
    service = build_fake_feedback_service()
    entity_id = uuid.uuid4()
    created = await service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="email_draft",
            entity_id=entity_id,
            rating=4,
            feedback_type="quality_issue",
            feedback_text="Too generic.",
        ),
        actor_user_id=None,
        actor_role=None,
    )
    assert created.entity_id == entity_id
    assert created.review_status == "open"
    assert created.is_blocking is False


async def test_create_feedback_truncates_overlong_text(monkeypatch):
    from backend.shared.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "quality_max_feedback_text_chars", 10)
    service = build_fake_feedback_service(settings=settings)
    created = await service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="email_draft",
            entity_id=uuid.uuid4(),
            rating=3,
            feedback_type="quality_issue",
            feedback_text="this text is definitely longer than ten chars",
        ),
        actor_user_id=None,
        actor_role=None,
    )
    assert len(created.feedback_text) == 10


async def test_blocking_feedback_is_counted_for_entity():
    service = build_fake_feedback_service()
    entity_id = uuid.uuid4()
    await service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="email_draft",
            entity_id=entity_id,
            rating=1,
            feedback_type="compliance_issue",
            is_blocking=True,
        ),
        actor_user_id=None,
        actor_role=None,
    )
    count = await service.count_blocking_for_entity("email_draft", entity_id)
    assert count == 1


async def test_review_feedback_updates_status():
    service = build_fake_feedback_service()
    created = await service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="email_draft",
            entity_id=uuid.uuid4(),
            rating=5,
            feedback_type="good_result",
        ),
        actor_user_id=None,
        actor_role=None,
    )
    reviewer_id = uuid.uuid4()
    updated = await service.review_feedback(
        created.id,
        ReviewQualityFeedbackRequest(review_status="accepted"),
        actor_user_id=reviewer_id,
        actor_role="admin",
    )
    assert updated.review_status == "accepted"
    assert updated.reviewed_by_user_id == reviewer_id


async def test_archive_feedback_sets_archived_status():
    service = build_fake_feedback_service()
    created = await service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="reply",
            entity_id=uuid.uuid4(),
            rating=2,
            feedback_type="bug",
        ),
        actor_user_id=None,
        actor_role=None,
    )
    archived = await service.archive_feedback(
        created.id, actor_user_id=None, actor_role="admin"
    )
    assert archived.review_status == "archived"


async def test_review_feedback_not_found_raises():
    service = build_fake_feedback_service()
    with pytest.raises(UserFeedbackNotFoundError):
        await service.review_feedback(
            uuid.uuid4(),
            ReviewQualityFeedbackRequest(review_status="accepted"),
            actor_user_id=None,
            actor_role="admin",
        )


async def test_rejected_blocking_feedback_no_longer_counts_as_blocker():
    service = build_fake_feedback_service()
    entity_id = uuid.uuid4()
    created = await service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="email_draft",
            entity_id=entity_id,
            rating=1,
            feedback_type="compliance_issue",
            is_blocking=True,
        ),
        actor_user_id=None,
        actor_role=None,
    )
    await service.review_feedback(
        created.id,
        ReviewQualityFeedbackRequest(review_status="rejected"),
        actor_user_id=None,
        actor_role="admin",
    )
    count = await service.count_blocking_for_entity("email_draft", entity_id)
    assert count == 0


# -- Phase 36: priority, general/UI feedback, Real-World Test Run linkage -----------


async def test_create_feedback_defaults_priority_to_medium():
    service = build_fake_feedback_service()
    created = await service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="email_draft",
            entity_id=uuid.uuid4(),
            rating=3,
            feedback_type="quality_issue",
        ),
        actor_user_id=None,
        actor_role=None,
    )
    assert created.priority == "medium"


async def test_create_feedback_accepts_explicit_priority():
    service = build_fake_feedback_service()
    created = await service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="email_draft",
            entity_id=uuid.uuid4(),
            rating=1,
            feedback_type="bug",
            priority="high",
        ),
        actor_user_id=None,
        actor_role=None,
    )
    assert created.priority == "high"


async def test_general_feedback_requires_no_entity_id():
    service = build_fake_feedback_service()
    created = await service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="general",
            rating=2,
            feedback_type="bug",
            feedback_text="Die Navigation ist verwirrend.",
        ),
        actor_user_id=None,
        actor_role=None,
    )
    assert created.entity_type == "general"
    assert created.entity_id is None


def test_create_quality_feedback_request_rejects_missing_entity_id_unless_general():
    with pytest.raises(ValueError):
        CreateQualityFeedbackRequest(
            entity_type="email_draft",
            rating=3,
            feedback_type="quality_issue",
        )


async def test_feedback_can_link_to_a_real_world_test_run():
    service = build_fake_feedback_service()
    run_id = uuid.uuid4()
    created = await service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="real_world_test_run",
            entity_id=run_id,
            rating=4,
            feedback_type="positive",
            real_world_test_run_id=run_id,
        ),
        actor_user_id=None,
        actor_role=None,
    )
    assert created.real_world_test_run_id == run_id


async def test_list_feedback_filters_by_priority():
    service = build_fake_feedback_service()
    await service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="email_draft",
            entity_id=uuid.uuid4(),
            rating=1,
            feedback_type="bug",
            priority="high",
        ),
        actor_user_id=None,
        actor_role=None,
    )
    await service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="email_draft",
            entity_id=uuid.uuid4(),
            rating=5,
            feedback_type="good_result",
            priority="low",
        ),
        actor_user_id=None,
        actor_role=None,
    )
    result = await service.list_feedback(priority="high")
    assert len(result.items) == 1
    assert result.items[0].priority == "high"
