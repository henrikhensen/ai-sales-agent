"""Quality Scoring and Feedback: rule-based (optionally LLM-assisted)
quality scores, plus structured human feedback on any scored entity.

Nothing here ever sends an email, contacts anyone, or changes an entity
automatically — scores and feedback are decision support only, reviewed
and acted on by a human separately.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.api.dependencies.auth import (
    RequireActiveUserDep,
    RequireReviewerOrAdminDep,
    RequireSalesReviewerOrAdminDep,
)
from backend.api.v1.dependencies import (
    FeedbackServiceDep,
    QualityDashboardServiceDep,
    QualityScoringServiceDep,
)
from backend.application.quality.feedback_schemas import (
    CreateQualityFeedbackRequest,
    QualityFeedbackDetailResponse,
    QualityFeedbackListResponse,
    QualityFeedbackResponse,
    ReviewQualityFeedbackRequest,
)
from backend.application.quality.quality_dashboard_schemas import (
    QualityDashboardResponse,
    QualityStatusResponse,
)
from backend.application.quality.quality_score_schemas import (
    CreateQualityScoreRequest,
    QualityScoreListResponse,
    QualityScoreResponse,
)
from backend.domain.exceptions import (
    QualityScoreNotFoundError,
    UserFeedbackNotFoundError,
)
from backend.shared.rate_limit import rate_limit

router = APIRouter(prefix="/quality", tags=["quality"])

_quality_scoring_rate_limit = Depends(
    rate_limit("quality_scoring", "rate_limit_quality_scoring_per_hour", 3600)
)
_quality_feedback_rate_limit = Depends(
    rate_limit("quality_feedback", "rate_limit_quality_feedback_per_hour", 3600)
)


@router.get("/status", response_model=QualityStatusResponse)
async def get_quality_status(
    service: QualityDashboardServiceDep,
    _current_user: RequireActiveUserDep,
) -> QualityStatusResponse:
    """Report current Quality Scoring / Feedback configuration. Any
    active, logged-in account may view this."""
    return service.get_status()


@router.get("/dashboard", response_model=QualityDashboardResponse)
async def get_quality_dashboard(
    service: QualityDashboardServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    request: Request,
) -> QualityDashboardResponse:
    """Aggregated quality overview. Decision support only — never a
    guarantee, and 'beta_ready' never means legal clearance."""
    return await service.get_dashboard(
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        http_request=request,
    )


@router.post(
    "/score",
    response_model=QualityScoreResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_quality_scoring_rate_limit],
)
async def create_quality_score(
    payload: CreateQualityScoreRequest,
    service: QualityScoringServiceDep,
    current_user: RequireSalesReviewerOrAdminDep,
    request: Request,
) -> QualityScoreResponse:
    """Compute an on-demand quality score for one entity. Rule-based by
    default; never sends an email or makes contact."""
    return await service.score_entity(
        payload,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        http_request=request,
    )


@router.get("/scores", response_model=QualityScoreListResponse)
async def list_quality_scores(
    service: QualityScoringServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    entity_type: str | None = Query(default=None),
    score_level: str | None = Query(default=None),
) -> QualityScoreListResponse:
    return await service.list_scores(
        limit=limit, offset=offset, entity_type=entity_type, score_level=score_level
    )


@router.get("/scores/{score_id}", response_model=QualityScoreResponse)
async def get_quality_score(
    score_id: UUID,
    service: QualityScoringServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> QualityScoreResponse:
    try:
        return await service.get_score(score_id)
    except QualityScoreNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/feedback",
    response_model=QualityFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_quality_feedback_rate_limit],
)
async def create_quality_feedback(
    payload: CreateQualityFeedbackRequest,
    service: FeedbackServiceDep,
    current_user: RequireActiveUserDep,
    request: Request,
) -> QualityFeedbackResponse:
    """Record feedback on any scored entity. Any active, logged-in account
    may give feedback. Never triggers any automatic action — no re-draft,
    no re-send, no automatic contact."""
    return await service.create_feedback(
        payload,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        http_request=request,
    )


@router.get("/feedback", response_model=QualityFeedbackListResponse)
async def list_quality_feedback(
    service: FeedbackServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    entity_type: str | None = Query(default=None),
    feedback_type: str | None = Query(default=None),
    rating: int | None = Query(default=None, ge=1, le=5),
    review_status: str | None = Query(default=None),
    is_blocking: bool | None = Query(default=None),
) -> QualityFeedbackListResponse:
    return await service.list_feedback(
        limit=limit,
        offset=offset,
        entity_type=entity_type,
        feedback_type=feedback_type,
        rating=rating,
        review_status=review_status,
        is_blocking=is_blocking,
    )


@router.get("/feedback/{feedback_id}", response_model=QualityFeedbackDetailResponse)
async def get_quality_feedback(
    feedback_id: UUID,
    service: FeedbackServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
) -> QualityFeedbackDetailResponse:
    try:
        return await service.get_feedback(feedback_id)
    except UserFeedbackNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/feedback/{feedback_id}/review",
    response_model=QualityFeedbackResponse,
    dependencies=[_quality_feedback_rate_limit],
)
async def review_quality_feedback(
    feedback_id: UUID,
    payload: ReviewQualityFeedbackRequest,
    service: FeedbackServiceDep,
    current_user: RequireReviewerOrAdminDep,
    request: Request,
) -> QualityFeedbackResponse:
    """Mark feedback as reviewed/accepted/rejected. Admin or reviewer only."""
    try:
        return await service.review_feedback(
            feedback_id,
            payload,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except UserFeedbackNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch(
    "/feedback/{feedback_id}/archive",
    response_model=QualityFeedbackResponse,
    dependencies=[_quality_feedback_rate_limit],
)
async def archive_quality_feedback(
    feedback_id: UUID,
    service: FeedbackServiceDep,
    current_user: RequireReviewerOrAdminDep,
    request: Request,
) -> QualityFeedbackResponse:
    """Archive feedback. Admin or reviewer only."""
    try:
        return await service.archive_feedback(
            feedback_id,
            actor_user_id=current_user.id,
            actor_role=current_user.role.value,
            http_request=request,
        )
    except UserFeedbackNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get(
    "/entity/{entity_type}/{entity_id}/scores", response_model=QualityScoreListResponse
)
async def get_entity_quality_scores(
    entity_type: str,
    entity_id: UUID,
    service: QualityScoringServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> QualityScoreListResponse:
    return await service.get_entity_scores(
        entity_type, entity_id, limit=limit, offset=offset
    )


@router.get(
    "/entity/{entity_type}/{entity_id}/feedback",
    response_model=QualityFeedbackListResponse,
)
async def get_entity_quality_feedback(
    entity_type: str,
    entity_id: UUID,
    service: FeedbackServiceDep,
    _current_user: RequireSalesReviewerOrAdminDep,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> QualityFeedbackListResponse:
    return await service.get_entity_feedback(
        entity_type, entity_id, limit=limit, offset=offset
    )
