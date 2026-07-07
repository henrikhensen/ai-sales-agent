"""Simple, process-local JSON metrics.

Deliberately not a Prometheus integration — see backend/shared/metrics.py.
Gated by ENABLE_METRICS (returns 404 when disabled, matching "this
capability does not exist here") and admin-only. Never includes personal
data, email/reply content, prompts, or secrets — only counts and aggregate
timings.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from backend.api.dependencies.auth import RequireAdminUserDep
from backend.api.v1.dependencies import SessionDep
from backend.api.v1.schemas.system import MetricsResponse
from backend.infrastructure.database.models.email_draft import EmailDraftModel
from backend.infrastructure.database.models.external_email_draft import (
    ExternalEmailDraftModel,
)
from backend.infrastructure.database.models.reply import ReplyModel
from backend.infrastructure.database.models.workflow_run import WorkflowRunModel
from backend.shared import metrics as metrics_module
from backend.shared.config import get_settings

router = APIRouter(prefix="/metrics", tags=["metrics"])


async def _count(session: SessionDep, model) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


@router.get("", response_model=MetricsResponse)
async def get_metrics(
    session: SessionDep,
    _current_user: RequireAdminUserDep,
) -> MetricsResponse:
    """Report request counters and entity counts. Admin-only; disabled
    (404) unless ``ENABLE_METRICS=true``."""
    settings = get_settings()
    if not settings.enable_metrics:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Metrics are disabled. Set ENABLE_METRICS=true to enable this endpoint.",
        )

    request_metrics = metrics_module.get_request_metrics()
    counters = metrics_module.get_counters()

    workflow_run_count = await _count(session, WorkflowRunModel)
    email_draft_count = await _count(session, EmailDraftModel)
    reply_count = await _count(session, ReplyModel)
    external_draft_created_count = await _count(session, ExternalEmailDraftModel)

    average_response_time_ms = (
        request_metrics.total_duration_ms / request_metrics.request_count
        if request_metrics.request_count
        else 0.0
    )

    return MetricsResponse(
        request_count=request_metrics.request_count,
        request_error_count=request_metrics.request_error_count,
        average_response_time_ms=round(average_response_time_ms, 2),
        workflow_run_count=workflow_run_count,
        email_draft_count=email_draft_count,
        reply_count=reply_count,
        do_not_contact_block_count=counters.do_not_contact_block_count,
        external_draft_created_count=external_draft_created_count,
        llm_test_count=counters.llm_test_count,
    )
