"""Tests for BetaTestService and QualityDashboardService using in-memory
fakes — no real database, no external calls, no real provider activation.
"""

import uuid

import pytest

from backend.application.quality.beta_test_schemas import CreateBetaTestSessionRequest
from backend.application.quality.feedback_schemas import CreateQualityFeedbackRequest
from backend.application.quality.quality_score_schemas import CreateQualityScoreRequest
from backend.domain.exceptions import (
    BetaTestSessionNotFoundError,
    InvalidBetaTestSessionTransitionError,
)
from tests.conftest import (
    FakeQualityScoreRepository,
    FakeUserFeedbackRepository,
    build_fake_beta_test_service,
    build_fake_feedback_service,
    build_fake_quality_dashboard_service,
    build_fake_quality_scoring_service,
)


async def test_create_session_defaults_to_planned():
    service = build_fake_beta_test_service()
    created = await service.create_session(
        CreateBetaTestSessionRequest(name="Round 1"),
        actor_user_id=None,
        actor_role=None,
    )
    assert created.status == "planned"


async def test_start_session_transitions_to_running():
    service = build_fake_beta_test_service()
    created = await service.create_session(
        CreateBetaTestSessionRequest(name="Round 1"),
        actor_user_id=None,
        actor_role=None,
    )
    started = await service.start_session(created.id, actor_user_id=None, actor_role=None)
    assert started.status == "running"
    assert started.started_at is not None


async def test_start_session_twice_raises():
    service = build_fake_beta_test_service()
    created = await service.create_session(
        CreateBetaTestSessionRequest(name="Round 1"),
        actor_user_id=None,
        actor_role=None,
    )
    await service.start_session(created.id, actor_user_id=None, actor_role=None)
    with pytest.raises(InvalidBetaTestSessionTransitionError):
        await service.start_session(created.id, actor_user_id=None, actor_role=None)


async def test_complete_session_not_started_raises_from_planned_is_allowed():
    # Spec allows completing directly from "planned" too (not just "running").
    service = build_fake_beta_test_service()
    created = await service.create_session(
        CreateBetaTestSessionRequest(name="Round 1"),
        actor_user_id=None,
        actor_role=None,
    )
    completed = await service.complete_session(created.id, actor_user_id=None, actor_role=None)
    assert completed.status == "completed"
    assert completed.completed_at is not None


async def test_complete_session_twice_raises():
    service = build_fake_beta_test_service()
    created = await service.create_session(
        CreateBetaTestSessionRequest(name="Round 1"),
        actor_user_id=None,
        actor_role=None,
    )
    await service.complete_session(created.id, actor_user_id=None, actor_role=None)
    with pytest.raises(InvalidBetaTestSessionTransitionError):
        await service.complete_session(created.id, actor_user_id=None, actor_role=None)


async def test_get_session_not_found_raises():
    service = build_fake_beta_test_service()
    with pytest.raises(BetaTestSessionNotFoundError):
        await service.get_session(uuid.uuid4())


async def test_complete_session_summarizes_scores_and_feedback():
    quality_scores = FakeQualityScoreRepository()
    feedback = FakeUserFeedbackRepository()
    scoring_service = build_fake_quality_scoring_service(quality_scores=quality_scores)
    feedback_service = build_fake_feedback_service(feedback=feedback)

    await scoring_service.auto_score("workflow_run", uuid.uuid4())
    await feedback_service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="email_draft",
            entity_id=uuid.uuid4(),
            rating=1,
            feedback_type="bug",
            is_blocking=True,
        ),
        actor_user_id=None,
        actor_role=None,
    )

    beta_service = build_fake_beta_test_service(
        quality_scores=quality_scores, feedback=feedback
    )
    created = await beta_service.create_session(
        CreateBetaTestSessionRequest(name="Round 1"),
        actor_user_id=None,
        actor_role=None,
    )
    completed = await beta_service.complete_session(
        created.id, actor_user_id=None, actor_role=None
    )
    assert completed.total_feedback_items == 1
    assert completed.blockers_count == 1
    assert completed.bugs_count == 1


async def test_beta_dashboard_not_ready_with_no_scores():
    service = build_fake_beta_test_service()
    dashboard = await service.get_dashboard()
    assert dashboard.readiness_level == "not_ready"


async def test_quality_dashboard_reflects_average_score_and_blocking_feedback():
    quality_scores = FakeQualityScoreRepository()
    feedback = FakeUserFeedbackRepository()
    scoring_service = build_fake_quality_scoring_service(quality_scores=quality_scores)
    feedback_service = build_fake_feedback_service(feedback=feedback)

    await scoring_service.score_entity(
        CreateQualityScoreRequest(entity_type="workflow_run", entity_id=uuid.uuid4()),
        actor_user_id=None,
        actor_role=None,
    )
    await feedback_service.create_feedback(
        CreateQualityFeedbackRequest(
            entity_type="workflow_run",
            entity_id=uuid.uuid4(),
            rating=1,
            feedback_type="compliance_issue",
            is_blocking=True,
        ),
        actor_user_id=None,
        actor_role=None,
    )

    dashboard_service = build_fake_quality_dashboard_service(
        quality_scores=quality_scores, feedback=feedback
    )
    dashboard = await dashboard_service.get_dashboard(actor_user_id=None, actor_role=None)
    assert dashboard.blocking_feedback_items == 1
    assert dashboard.total_feedback_items == 1
