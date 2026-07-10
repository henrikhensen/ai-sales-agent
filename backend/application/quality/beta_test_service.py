"""Beta Test Sessions: structured tracking of manual beta testing rounds.

A session is a tracking/aggregation record only — creating, starting, or
completing one never activates a real provider, sends an email, or
creates an external draft automatically. Quality scores and feedback are
not linked to a specific session in this phase (see CUSTOMER_READINESS.md
"Known Limitations") — a session's summary reflects the system-wide
aggregate at the time it is completed, not a per-session subset.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.quality.beta_test_schemas import (
    BetaTestDashboardResponse,
    BetaTestSessionListResponse,
    BetaTestSessionResponse,
    CreateBetaTestSessionRequest,
)
from backend.application.quality.readiness import compute_beta_readiness
from backend.domain.entities.beta_test_session import BetaTestSession
from backend.domain.exceptions import (
    BetaTestSessionNotFoundError,
    InvalidBetaTestSessionTransitionError,
)
from backend.domain.repositories.beta_test_session_repository import (
    BetaTestSessionRepository,
)
from backend.domain.repositories.quality_score_repository import (
    QualityScoreRepository,
)
from backend.domain.repositories.user_feedback_repository import (
    UserFeedbackRepository,
)
from backend.shared.config import Settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BetaTestService:
    def __init__(
        self,
        sessions: BetaTestSessionRepository,
        quality_scores: QualityScoreRepository,
        feedback: UserFeedbackRepository,
        audit: AuditLogService,
        settings: Settings,
    ) -> None:
        self._sessions = sessions
        self._quality_scores = quality_scores
        self._feedback = feedback
        self._audit = audit
        self._settings = settings

    async def create_session(
        self,
        request: CreateBetaTestSessionRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> BetaTestSessionResponse:
        created = await self._sessions.create(
            BetaTestSession(
                name=request.name,
                description=request.description,
                target_goal=request.target_goal,
                tester_user_id=actor_user_id,
            )
        )
        await self._audit.record(
            action="beta_test_session_created",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="beta_test_session",
            entity_id=created.id,
            request=http_request,
        )
        return BetaTestSessionResponse.model_validate(created)

    async def list_sessions(
        self, limit: int = 100, offset: int = 0, status: str | None = None
    ) -> BetaTestSessionListResponse:
        items = await self._sessions.list(limit=limit, offset=offset, status=status)
        return BetaTestSessionListResponse(
            items=[BetaTestSessionResponse.model_validate(s) for s in items],
            limit=limit,
            offset=offset,
        )

    async def _get_or_404(self, session_id: UUID) -> BetaTestSession:
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise BetaTestSessionNotFoundError(session_id)
        return session

    async def get_session(self, session_id: UUID) -> BetaTestSessionResponse:
        session = await self._get_or_404(session_id)
        return BetaTestSessionResponse.model_validate(session)

    async def start_session(
        self,
        session_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> BetaTestSessionResponse:
        session = await self._get_or_404(session_id)
        if session.status != "planned":
            raise InvalidBetaTestSessionTransitionError(session.status, "running")
        session.status = "running"
        session.started_at = _now()
        updated = await self._sessions.update(session)
        assert updated is not None
        await self._audit.record(
            action="beta_test_session_started",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="beta_test_session",
            entity_id=updated.id,
            request=http_request,
        )
        return BetaTestSessionResponse.model_validate(updated)

    async def complete_session(
        self,
        session_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> BetaTestSessionResponse:
        session = await self._get_or_404(session_id)
        if session.status not in ("planned", "running"):
            raise InvalidBetaTestSessionTransitionError(session.status, "completed")

        scores = await self._quality_scores.list_all_latest(limit=2000)
        feedback_items = await self._feedback.list(limit=2000)
        session.total_workflows_tested = sum(
            1 for s in scores if s.entity_type == "workflow_run"
        )
        session.total_drafts_reviewed = sum(
            1 for s in scores if s.entity_type == "email_draft"
        )
        session.total_feedback_items = len(feedback_items)
        session.blockers_count = sum(1 for f in feedback_items if f.is_blocking)
        session.bugs_count = sum(1 for f in feedback_items if f.feedback_type == "bug")
        if scores:
            session.average_quality_score = sum(s.score_total for s in scores) / len(scores)
        session.status = "completed"
        session.completed_at = _now()

        updated = await self._sessions.update(session)
        assert updated is not None
        await self._audit.record(
            action="beta_test_session_completed",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="beta_test_session",
            entity_id=updated.id,
            metadata={
                "average_quality_score": updated.average_quality_score,
                "blockers_count": updated.blockers_count,
                "bugs_count": updated.bugs_count,
            },
            request=http_request,
        )
        return BetaTestSessionResponse.model_validate(updated)

    async def get_dashboard(self) -> BetaTestDashboardResponse:
        sessions = await self._sessions.list(limit=500)
        scores = await self._quality_scores.list_all_latest(limit=2000)
        open_feedback = await self._feedback.list(limit=2000, review_status="open")
        blocking_feedback = await self._feedback.list(limit=2000, is_blocking=True)
        all_feedback = await self._feedback.list(limit=2000)

        average_score = (
            sum(s.score_total for s in scores) / len(scores) if scores else None
        )
        open_blocking = [
            f for f in blocking_feedback if f.review_status in ("open", "reviewed", "accepted")
        ]
        bugs = sum(1 for f in all_feedback if f.feedback_type == "bug")

        readiness_level, recommendations, warnings = compute_beta_readiness(
            settings=self._settings,
            average_quality_score=average_score,
            total_feedback_items=len(all_feedback),
            blocking_feedback_items=len(open_blocking),
            total_scores=len(scores),
        )

        return BetaTestDashboardResponse(
            sessions_count=len(sessions),
            running_sessions_count=sum(1 for s in sessions if s.status == "running"),
            completed_sessions_count=sum(1 for s in sessions if s.status == "completed"),
            average_quality_score=average_score,
            total_feedback_items=len(all_feedback),
            open_feedback_items=len(open_feedback),
            blocking_feedback_items=len(open_blocking),
            total_bugs=bugs,
            readiness_level=readiness_level,
            recommendations=recommendations,
            warnings=warnings,
            message=(
                "Beta readiness is a technical signal only — it never means "
                "legal clearance or that the product is automatically "
                "market-ready. See CUSTOMER_READINESS.md."
            ),
        )
