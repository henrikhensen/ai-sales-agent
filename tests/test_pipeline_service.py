"""Tests for PipelineService using the in-memory FakeLeadRepository — no
real database, no external calls of any kind.
"""

import uuid

import pytest

from backend.application.crm.pipeline_service import PipelineService
from backend.domain.entities.lead import Lead
from backend.domain.enums import LeadSource, PipelineStatus, WorkflowReviewStatus
from backend.domain.exceptions import LeadNotFoundError
from tests.conftest import FakeLeadRepository


async def _seed_lead(leads: FakeLeadRepository, **overrides) -> Lead:
    defaults = dict(company_id=uuid.uuid4(), source=LeadSource.OUTBOUND)
    defaults.update(overrides)
    return await leads.create(Lead(**defaults))


async def test_get_board_groups_leads_by_pipeline_status():
    leads = FakeLeadRepository()
    service = PipelineService(leads)
    lead_new = await _seed_lead(leads)
    lead_draft = await _seed_lead(leads)
    await leads.update_pipeline_status(lead_draft.id, PipelineStatus.DRAFT_CREATED)

    board = await service.get_board()

    # Every known status gets a column, even empty ones.
    assert {column.pipeline_status for column in board.columns} == set(PipelineStatus)

    new_column = next(c for c in board.columns if c.pipeline_status == PipelineStatus.NEW)
    draft_column = next(
        c for c in board.columns if c.pipeline_status == PipelineStatus.DRAFT_CREATED
    )
    archived_column = next(
        c for c in board.columns if c.pipeline_status == PipelineStatus.ARCHIVED
    )

    assert [lead.id for lead in new_column.leads] == [lead_new.id]
    assert [lead.id for lead in draft_column.leads] == [lead_draft.id]
    assert archived_column.leads == []


async def test_update_lead_pipeline_status_sets_status_and_timestamp():
    leads = FakeLeadRepository()
    service = PipelineService(leads)
    lead = await _seed_lead(leads)

    result = await service.update_lead_pipeline_status(lead.id, PipelineStatus.IN_REVIEW)

    assert result.pipeline_status == PipelineStatus.IN_REVIEW
    assert result.pipeline_updated_at is not None


async def test_update_lead_pipeline_status_raises_for_unknown_lead():
    leads = FakeLeadRepository()
    service = PipelineService(leads)

    with pytest.raises(LeadNotFoundError):
        await service.update_lead_pipeline_status(uuid.uuid4(), PipelineStatus.ARCHIVED)


async def test_sync_from_workflow_review_status_maps_approved():
    leads = FakeLeadRepository()
    service = PipelineService(leads)
    lead = await _seed_lead(leads)

    await service.sync_from_workflow_review_status(lead.id, WorkflowReviewStatus.APPROVED)

    updated = await leads.get(lead.id)
    assert updated.pipeline_status == PipelineStatus.APPROVED


async def test_sync_from_workflow_review_status_maps_rejected():
    leads = FakeLeadRepository()
    service = PipelineService(leads)
    lead = await _seed_lead(leads)

    await service.sync_from_workflow_review_status(lead.id, WorkflowReviewStatus.REJECTED)

    updated = await leads.get(lead.id)
    assert updated.pipeline_status == PipelineStatus.REJECTED


async def test_sync_from_workflow_review_status_ignores_other_statuses():
    leads = FakeLeadRepository()
    service = PipelineService(leads)
    lead = await _seed_lead(leads)
    await leads.update_pipeline_status(lead.id, PipelineStatus.DRAFT_CREATED)

    await service.sync_from_workflow_review_status(lead.id, WorkflowReviewStatus.REVIEWED)

    updated = await leads.get(lead.id)
    assert updated.pipeline_status == PipelineStatus.DRAFT_CREATED


async def test_sync_from_workflow_review_status_is_a_no_op_for_unknown_lead():
    leads = FakeLeadRepository()
    service = PipelineService(leads)

    # Must not raise even though the lead doesn't exist — this is a
    # best-effort side effect, not the primary action.
    await service.sync_from_workflow_review_status(
        uuid.uuid4(), WorkflowReviewStatus.APPROVED
    )
