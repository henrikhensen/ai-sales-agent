"""Tests for the domain-level PipelineStatus enum and Lead defaults."""

import uuid

from backend.domain.entities.lead import Lead
from backend.domain.enums import LeadSource, PipelineStatus


def test_pipeline_status_has_exactly_the_expected_values():
    assert {status.value for status in PipelineStatus} == {
        "new",
        "research_completed",
        "draft_created",
        "in_review",
        "approved",
        "rejected",
        "archived",
    }


def test_lead_default_pipeline_status_is_new():
    lead = Lead(company_id=uuid.uuid4(), source=LeadSource.OUTBOUND)

    assert lead.pipeline_status == PipelineStatus.NEW
    assert lead.pipeline_updated_at is None
