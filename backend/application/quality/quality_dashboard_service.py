"""Quality Dashboard: aggregates quality scores and feedback into a
single overview. Read-only — never changes anything. All figures here are
decision support only, never a guarantee and never a legal clearance.
"""

from __future__ import annotations

from collections import Counter
from uuid import UUID

from fastapi import Request

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.quality.quality_dashboard_schemas import (
    EntityScoreSummary,
    QualityDashboardResponse,
    QualityIssueSummary,
    QualityStatusResponse,
)
from backend.application.quality.readiness import compute_beta_readiness
from backend.domain.repositories.quality_score_repository import (
    QualityScoreRepository,
)
from backend.domain.repositories.user_feedback_repository import (
    UserFeedbackRepository,
)
from backend.shared.config import Settings

_TOP_N = 10
_BEST_WORST_N = 5


class QualityDashboardService:
    def __init__(
        self,
        quality_scores: QualityScoreRepository,
        feedback: UserFeedbackRepository,
        audit: AuditLogService,
        settings: Settings,
    ) -> None:
        self._quality_scores = quality_scores
        self._feedback = feedback
        self._audit = audit
        self._settings = settings

    def get_status(self) -> QualityStatusResponse:
        return QualityStatusResponse(
            quality_feedback_enabled=self._settings.quality_feedback_enabled,
            quality_scoring_enabled=self._settings.quality_scoring_enabled,
            quality_scoring_provider=self._settings.quality_scoring_provider,
            quality_scoring_use_llm=self._settings.quality_scoring_use_llm,
            min_draft_score=self._settings.quality_min_draft_score,
            min_lead_score=self._settings.quality_min_lead_score,
            min_workflow_score=self._settings.quality_min_workflow_score,
            auto_score_drafts=self._settings.quality_auto_score_drafts,
            auto_score_workflows=self._settings.quality_auto_score_workflows,
            require_human_feedback_for_beta=(
                self._settings.quality_require_human_feedback_for_beta
            ),
            message=(
                "Quality scores are decision support only — never a "
                "guarantee, and never a substitute for Human Review or "
                "Do-not-contact."
            ),
        )

    async def get_dashboard(
        self,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> QualityDashboardResponse:
        scores = await self._quality_scores.list_all_latest(limit=2000)
        draft_scores = [s for s in scores if s.entity_type == "email_draft"]
        lead_scores = [
            s for s in scores if s.entity_type in ("lead_candidate", "crm_lead")
        ]
        workflow_scores = [s for s in scores if s.entity_type == "workflow_run"]

        def _avg(items: list) -> float | None:
            return sum(s.score_total for s in items) / len(items) if items else None

        all_feedback = await self._feedback.list(limit=2000)
        open_feedback = [f for f in all_feedback if f.review_status == "open"]
        blocking_feedback = [
            f
            for f in all_feedback
            if f.is_blocking and f.review_status in ("open", "reviewed", "accepted")
        ]

        issue_counter: Counter[str] = Counter()
        improvement_counter: Counter[str] = Counter()
        for f in all_feedback:
            issue_counter.update(f.issue_tags)
            improvement_counter.update(f.improvement_tags)

        def _sorted_summaries(items: list, reverse: bool) -> list[EntityScoreSummary]:
            ordered = sorted(items, key=lambda s: s.score_total, reverse=reverse)
            return [
                EntityScoreSummary(
                    entity_type=s.entity_type,
                    entity_id=s.entity_id,
                    score_total=s.score_total,
                    score_level=s.score_level,
                )
                for s in ordered[:_BEST_WORST_N]
            ]

        readiness_level, recommendations, warnings = compute_beta_readiness(
            settings=self._settings,
            average_quality_score=_avg(scores),
            total_feedback_items=len(all_feedback),
            blocking_feedback_items=len(blocking_feedback),
            total_scores=len(scores),
        )

        response = QualityDashboardResponse(
            average_draft_quality_score=_avg(draft_scores),
            average_lead_quality_score=_avg(lead_scores),
            average_workflow_quality_score=_avg(workflow_scores),
            total_feedback_items=len(all_feedback),
            open_feedback_items=len(open_feedback),
            blocking_feedback_items=len(blocking_feedback),
            top_quality_issues=[
                QualityIssueSummary(tag=tag, count=count)
                for tag, count in issue_counter.most_common(_TOP_N)
            ],
            top_improvement_suggestions=[
                QualityIssueSummary(tag=tag, count=count)
                for tag, count in improvement_counter.most_common(_TOP_N)
            ],
            best_performing_drafts=_sorted_summaries(draft_scores, reverse=True),
            weakest_drafts=_sorted_summaries(draft_scores, reverse=False),
            best_leads=_sorted_summaries(lead_scores, reverse=True),
            weakest_leads=_sorted_summaries(lead_scores, reverse=False),
            beta_readiness_level=readiness_level,
            warnings=warnings,
            message=(
                "Quality scores and feedback here are decision support only. "
                "'beta_ready' is a technical signal, not a legal clearance — "
                "see CUSTOMER_READINESS.md."
            ),
        )
        await self._audit.record(
            action="quality_dashboard_viewed",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="quality_dashboard",
            metadata={"beta_readiness_level": readiness_level},
            request=http_request,
        )
        return response
