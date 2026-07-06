import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.application.crm.pipeline_schemas import (
    LeadPipelineSummary,
    PipelineBoardResponse,
    PipelineColumn,
    UpdateLeadPipelineStatusRequest,
)
from backend.domain.enums import PipelineStatus


def test_update_request_accepts_allowed_status():
    request = UpdateLeadPipelineStatusRequest(pipeline_status="in_review")
    assert request.pipeline_status == PipelineStatus.IN_REVIEW


def test_update_request_rejects_invalid_status():
    with pytest.raises(ValidationError):
        UpdateLeadPipelineStatusRequest(pipeline_status="not-a-real-status")


def _lead_summary(**overrides) -> LeadPipelineSummary:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        pipeline_status=PipelineStatus.NEW,
        pipeline_updated_at=None,
        score=0,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return LeadPipelineSummary(**defaults)


def test_pipeline_column_holds_its_leads():
    column = PipelineColumn(
        pipeline_status=PipelineStatus.DRAFT_CREATED,
        leads=[_lead_summary(pipeline_status=PipelineStatus.DRAFT_CREATED)],
    )
    assert column.pipeline_status == PipelineStatus.DRAFT_CREATED
    assert len(column.leads) == 1


def test_pipeline_board_response_holds_columns():
    board = PipelineBoardResponse(
        columns=[
            PipelineColumn(pipeline_status=PipelineStatus.NEW, leads=[_lead_summary()]),
            PipelineColumn(pipeline_status=PipelineStatus.ARCHIVED, leads=[]),
        ]
    )
    assert len(board.columns) == 2
    assert board.columns[1].leads == []
