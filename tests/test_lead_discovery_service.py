"""Tests for the Lead Discovery Service ("Lead Finder").

Covers: run creation (and its underlying Lead Sourcing Campaign / Outreach
Campaign), the real_llm mode gate, offer/ICP not-found errors, the full
pipeline (find -> analyze website quality -> qualify -> queue eligible
candidates), do-not-contact blocking during the pipeline, the guard against
re-running a completed/running pipeline, draft creation as a separate
explicit action gated on pipeline completion, the manual per-candidate
queue override, and the standing rule that nothing here is send-capable.
"""

import uuid

import pytest

from backend.application.compliance.schemas import CreateDoNotContactRequest
from backend.application.lead_discovery.schemas import CreateLeadDiscoveryRunRequest
from backend.application.outreach.outreach_queue_service import OutreachQueueService
from backend.domain.entities.icp_profile import ICPProfile
from backend.domain.entities.offer_profile import OfferProfile
from backend.domain.entities.outreach_queue_item import OutreachQueueItem
from backend.domain.exceptions import (
    ICPProfileNotFoundError,
    InvalidLeadDiscoveryRunTransitionError,
    LeadDiscoveryModeNotAllowedError,
    LeadDiscoveryRunNotFoundError,
    OfferProfileNotFoundError,
)
from tests.conftest import (
    FakeICPProfileRepository,
    FakeOfferProfileRepository,
    build_fake_compliance_service,
    build_fake_icp_service,
    build_fake_lead_discovery_service,
    build_fake_offer_service,
)


async def _make_offer() -> tuple[uuid.UUID, object]:
    repo = FakeOfferProfileRepository()
    offer = await repo.create(
        OfferProfile(name="Test Offer", main_value_proposition="We help you sell more.")
    )
    return offer.id, build_fake_offer_service(offer_profiles=repo)


def _request(offer_id: uuid.UUID, **overrides) -> CreateLeadDiscoveryRunRequest:
    payload = {
        "target_customer": "Software",
        "region": "Berlin",
        "offer_profile_id": offer_id,
        "requested_count": 5,
        "min_score": 0,
        **overrides,
    }
    return CreateLeadDiscoveryRunRequest(**payload)


# -- create_run ---------------------------------------------------------------------


async def test_create_run_creates_underlying_sourcing_and_outreach_campaigns():
    offer_id, offer_service = await _make_offer()
    service = build_fake_lead_discovery_service(offer_service=offer_service)

    run = await service.create_run(
        _request(offer_id), actor_user_id=None, actor_role="sales"
    )

    assert run.status == "pending"
    assert run.mode == "mock"
    assert run.lead_sourcing_campaign_id is not None
    assert run.outreach_campaign_id is not None
    assert run.found_candidates == 0


async def test_create_run_rejects_real_llm_without_real_calls_enabled():
    offer_id, offer_service = await _make_offer()
    service = build_fake_lead_discovery_service(offer_service=offer_service)
    assert service._settings.llm_enable_real_calls is False

    with pytest.raises(LeadDiscoveryModeNotAllowedError):
        await service.create_run(
            _request(offer_id, mode="real_llm"), actor_user_id=None, actor_role="sales"
        )


async def test_create_run_with_unknown_offer_raises():
    service = build_fake_lead_discovery_service()
    with pytest.raises(OfferProfileNotFoundError):
        await service.create_run(
            _request(uuid.uuid4()), actor_user_id=None, actor_role="sales"
        )


async def test_create_run_with_unknown_icp_raises():
    offer_id, offer_service = await _make_offer()
    service = build_fake_lead_discovery_service(offer_service=offer_service)
    with pytest.raises(ICPProfileNotFoundError):
        await service.create_run(
            _request(offer_id, icp_profile_id=uuid.uuid4()),
            actor_user_id=None,
            actor_role="sales",
        )


# -- run_pipeline ---------------------------------------------------------------------


async def test_run_pipeline_finds_and_qualifies_candidates():
    offer_id, offer_service = await _make_offer()
    service = build_fake_lead_discovery_service(offer_service=offer_service)
    run = await service.create_run(
        _request(offer_id), actor_user_id=None, actor_role="sales"
    )

    detail = await service.run_pipeline(run.id, actor_user_id=None, actor_role="sales")

    assert detail.status == "completed"
    assert detail.found_candidates >= 1
    assert detail.found_candidates == detail.qualified_leads + detail.rejected_leads
    assert len(detail.candidates) == detail.found_candidates
    # Every found candidate with a website URL got a website quality
    # assessment from data already fetched during sourcing.
    for candidate in detail.candidates:
        if candidate.company_website_url:
            assert candidate.website_quality_level in ("poor", "medium", "good", "unknown")


async def test_run_pipeline_rejects_a_do_not_contact_blocked_candidate_without_qualifying_it():
    offer_id, offer_service = await _make_offer()
    compliance = build_fake_compliance_service()
    # The mock lead sourcing provider's "Software"/"Berlin" match is
    # Blauwerk SaaS Solutions at blauwerk-saas.example — block its domain.
    await compliance.create_entry(
        CreateDoNotContactRequest(domain="blauwerk-saas.example", reason="test block"),
        created_by_user_id=None,
    )
    service = build_fake_lead_discovery_service(
        offer_service=offer_service, compliance=compliance
    )
    run = await service.create_run(
        _request(offer_id), actor_user_id=None, actor_role="sales"
    )

    detail = await service.run_pipeline(run.id, actor_user_id=None, actor_role="sales")

    assert detail.status == "completed"
    assert detail.found_candidates >= 1
    blocked = [c for c in detail.candidates if c.do_not_contact_status == "blocked"]
    assert blocked
    assert detail.qualified_leads == 0
    assert detail.rejected_leads == detail.found_candidates


async def test_run_pipeline_cannot_be_rerun_once_completed():
    offer_id, offer_service = await _make_offer()
    service = build_fake_lead_discovery_service(offer_service=offer_service)
    run = await service.create_run(
        _request(offer_id), actor_user_id=None, actor_role="sales"
    )
    await service.run_pipeline(run.id, actor_user_id=None, actor_role="sales")

    with pytest.raises(InvalidLeadDiscoveryRunTransitionError):
        await service.run_pipeline(run.id, actor_user_id=None, actor_role="sales")


async def test_run_pipeline_unknown_run_raises_not_found():
    service = build_fake_lead_discovery_service()
    with pytest.raises(LeadDiscoveryRunNotFoundError):
        await service.run_pipeline(uuid.uuid4(), actor_user_id=None, actor_role="sales")


# -- create_drafts_for_qualified_candidates --------------------------------------------


async def test_create_drafts_before_pipeline_runs_is_rejected():
    offer_id, offer_service = await _make_offer()
    service = build_fake_lead_discovery_service(offer_service=offer_service)
    run = await service.create_run(
        _request(offer_id), actor_user_id=None, actor_role="sales"
    )

    with pytest.raises(InvalidLeadDiscoveryRunTransitionError):
        await service.create_drafts_for_qualified_candidates(
            run.id, actor_user_id=None, actor_role="sales"
        )


async def test_create_drafts_prepares_a_draft_for_a_queued_candidate():
    """Arranges a queue item already in 'queued' status (as build_queue
    would leave a clearly 'qualified'/'priority' result) directly via the
    fake repo, isolating this unit from the mock scoring engine's
    borderline-score randomness — the same OutreachQueueService.
    prepare_batch this wraps is already covered end-to-end in
    test_outreach_queue_service.py."""
    offer_id, offer_service = await _make_offer()
    service = build_fake_lead_discovery_service(offer_service=offer_service)
    run = await service.create_run(
        _request(offer_id), actor_user_id=None, actor_role="sales"
    )
    detail = await service.run_pipeline(run.id, actor_user_id=None, actor_role="sales")
    assert detail.candidates, "mock provider should have found at least one candidate"

    candidate = detail.candidates[0]
    await service._queue_items.create(
        OutreachQueueItem(
            campaign_id=run.outreach_campaign_id,
            lead_candidate_id=candidate.candidate_id,
            qualification_score=90,
            qualification_level="excellent",
            queue_status="queued",
        )
    )

    result = await service.create_drafts_for_qualified_candidates(
        run.id, actor_user_id=None, actor_role="sales"
    )

    assert result.created_drafts == 1
    updated_candidate = next(
        c for c in result.candidates if c.candidate_id == candidate.candidate_id
    )
    assert updated_candidate.draft_status in ("review_pending", "prepared")
    if updated_candidate.draft_status == "review_pending":
        assert updated_candidate.email_draft_id is not None


async def test_create_drafts_unknown_run_raises_not_found():
    service = build_fake_lead_discovery_service()
    with pytest.raises(LeadDiscoveryRunNotFoundError):
        await service.create_drafts_for_qualified_candidates(
            uuid.uuid4(), actor_user_id=None, actor_role="sales"
        )


# -- add_candidate_to_queue (manual override) ------------------------------------------


async def test_add_candidate_to_queue_without_qualification_result_is_not_added():
    offer_id, offer_service = await _make_offer()
    service = build_fake_lead_discovery_service(offer_service=offer_service)
    run = await service.create_run(
        _request(offer_id), actor_user_id=None, actor_role="sales"
    )
    await service.run_pipeline(run.id, actor_user_id=None, actor_role="sales")

    response = await service.add_candidate_to_queue(
        run.id, uuid.uuid4(), actor_user_id=None, actor_role="sales"
    )

    assert response.added is False
    assert response.warnings


async def test_add_candidate_to_queue_manually_queues_a_qualified_result():
    offer_id, offer_service = await _make_offer()
    service = build_fake_lead_discovery_service(offer_service=offer_service)
    run = await service.create_run(
        _request(offer_id), actor_user_id=None, actor_role="sales"
    )
    detail = await service.run_pipeline(run.id, actor_user_id=None, actor_role="sales")
    candidate = detail.candidates[0]

    response = await service.add_candidate_to_queue(
        run.id, candidate.candidate_id, actor_user_id=None, actor_role="sales"
    )

    assert response.added is True


# -- safety: nothing here is send-capable ----------------------------------------------


def test_no_method_on_the_service_is_send_shaped():
    service_methods = [name for name in dir(OutreachQueueService) if not name.startswith("_")]
    from backend.application.lead_discovery.lead_discovery_service import (
        LeadDiscoveryService,
    )

    lead_discovery_methods = [
        name for name in dir(LeadDiscoveryService) if not name.startswith("_")
    ]
    for name in (*service_methods, *lead_discovery_methods):
        assert "send" not in name.lower()
