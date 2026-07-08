"""Tests for the Outreach Campaign Queue.

Covers: campaign CRUD, queue build (including dry-run and do-not-contact/
duplicate/disqualified handling), queue item status transitions, single-item
and batch Sales Workflow preparation (via the real Sales Workflow running
against the deterministic MockLLMProvider — never a network call), the
dashboard, and the hard rule that nothing here ever sends an email, creates
an external draft, or introduces a 'sent' status.
"""

import uuid

import pytest

from backend.application.compliance.schemas import CreateDoNotContactRequest
from backend.application.outreach.schemas import (
    BuildOutreachQueueRequest,
    CreateOutreachCampaignRequest,
    PrepareQueueBatchRequest,
    PrepareQueueItemWorkflowRequest,
    UpdateOutreachCampaignRequest,
    UpdateOutreachCampaignStatusRequest,
    UpdateQueueItemStatusRequest,
)
from backend.domain.entities.company import Company
from backend.domain.entities.lead import Lead
from backend.domain.entities.qualification_result import QualificationResult
from backend.domain.enums import LeadSource
from backend.domain.exceptions import (
    InvalidOutreachQueueStatusTransitionError,
    OutreachCampaignNotFoundError,
    OutreachQueueItemBlockedError,
    OutreachQueueItemNotFoundError,
)
from tests.conftest import (
    FakeCompanyRepository,
    FakeLeadRepository,
    FakeQualificationResultRepository,
    build_fake_compliance_service,
    build_fake_outreach_queue_service,
)


async def _seed_lead_and_result(
    companies: FakeCompanyRepository,
    leads: FakeLeadRepository,
    results: FakeQualificationResultRepository,
    *,
    domain: str = "acme.example.com",
    score: int = 90,
    level: str = "excellent",
    status: str = "priority",
    duplicate_status: str = "new",
    compliance_status: str = "clear",
):
    company = await companies.create(Company(name="Acme GmbH", domain=domain, industry="Logistics"))
    lead = await leads.create(Lead(company_id=company.id, source=LeadSource.OUTBOUND))
    result = await results.create(
        QualificationResult(
            qualification_run_id=uuid.uuid4(),
            lead_id=lead.id,
            company_id=company.id,
            qualification_score=score,
            qualification_level=level,
            qualification_status=status,
            recommended_outreach_angle="Mention fleet visibility pain point.",
            fit_summary="Strong ICP match.",
            duplicate_status=duplicate_status,
            compliance_status=compliance_status,
            do_not_contact_status="clear" if compliance_status == "clear" else "blocked",
        )
    )
    return company, lead, result


def _build_wiring():
    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    results = FakeQualificationResultRepository()
    compliance = build_fake_compliance_service()
    service = build_fake_outreach_queue_service(
        companies=companies, leads=leads, qualification_results=results, compliance=compliance
    )
    return service, companies, leads, results, compliance


async def _create_campaign(service, **overrides):
    payload = CreateOutreachCampaignRequest(name="Q3 Logistics Push", **overrides)
    return await service.create_campaign(payload, actor_user_id=None, actor_role="sales")


# -- campaigns --------------------------------------------------------------------


async def test_campaign_kann_erstellt_werden():
    service, *_ = _build_wiring()
    campaign = await _create_campaign(service)
    assert campaign.status == "draft"
    assert campaign.name == "Q3 Logistics Push"


async def test_campaign_kann_aktualisiert_werden():
    service, *_ = _build_wiring()
    campaign = await _create_campaign(service)
    updated = await service.update_campaign(
        campaign.id,
        UpdateOutreachCampaignRequest(name="Renamed", min_qualification_score=80),
        actor_user_id=None,
        actor_role="sales",
    )
    assert updated.name == "Renamed"
    assert updated.min_qualification_score == 80


async def test_campaign_kann_archiviert_werden():
    service, *_ = _build_wiring()
    campaign = await _create_campaign(service)
    archived = await service.archive_campaign(campaign.id, actor_user_id=None, actor_role="admin")
    assert archived.status == "archived"


async def test_archivierte_campaign_kann_nicht_reaktiviert_werden():
    service, *_ = _build_wiring()
    campaign = await _create_campaign(service)
    await service.archive_campaign(campaign.id, actor_user_id=None, actor_role="admin")
    with pytest.raises(InvalidOutreachQueueStatusTransitionError):
        await service.set_campaign_status(
            campaign.id,
            UpdateOutreachCampaignStatusRequest(status="active").status,
            actor_user_id=None,
            actor_role="admin",
        )


async def test_unbekannte_campaign_wirft_not_found():
    service, *_ = _build_wiring()
    with pytest.raises(OutreachCampaignNotFoundError):
        await service.get_campaign(uuid.uuid4())


# -- queue build --------------------------------------------------------------------


async def test_queue_kann_aus_qualification_results_gebaut_werden():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    _, lead, result = await _seed_lead_and_result(companies, leads, results)

    response = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )

    assert response.dry_run is False
    assert len(response.items) == 1
    item = response.items[0]
    assert item.id is not None
    assert item.queue_status == "queued"
    assert item.qualification_score == 90
    assert item.recommended_outreach_angle == "Mention fleet visibility pain point."


async def test_dry_run_speichert_keine_queue_items():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results)

    response = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id], dry_run=True),
        actor_user_id=None,
        actor_role="sales",
    )

    assert response.dry_run is True
    assert len(response.items) == 1
    assert response.items[0].id is None

    listed = await service.list_queue_items(campaign_id=campaign.id)
    assert listed.items == []


async def test_do_not_contact_setzt_status_blocked():
    service, companies, leads, results, compliance = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results, domain="blocked.example.com")
    await compliance.create_entry(
        CreateDoNotContactRequest(domain="blocked.example.com", reason="opted out"),
        created_by_user_id=None,
    )

    response = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )

    assert response.blocked_count == 1
    assert response.items[0].queue_status == "blocked"
    assert response.items[0].compliance_status == "blocked"


async def test_duplicate_wird_nicht_doppelt_bearbeitet():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(
        companies, leads, results, duplicate_status="duplicate"
    )

    response = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )

    assert response.items == []
    assert response.skipped_count == 1


async def test_disqualified_wird_ausgeschlossen():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(
        companies, leads, results, status="disqualified", score=20, level="not_fit"
    )

    response = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )

    assert response.items == []
    assert response.skipped_count == 1


async def test_score_unter_min_score_wird_ausgeschlossen():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results, score=50)

    response = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id], min_score=70),
        actor_user_id=None,
        actor_role="sales",
    )

    assert response.items == []
    assert response.skipped_count == 1


async def test_needs_review_qualification_wird_als_needs_review_gequeued():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results, status="needs_review")

    response = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id], min_score=0),
        actor_user_id=None,
        actor_role="sales",
    )

    assert response.items[0].queue_status == "needs_review"


# -- status transitions ---------------------------------------------------------------


async def test_gueltiger_status_uebergang_funktioniert():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results)
    built = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )
    item_id = built.items[0].id

    updated = await service.update_queue_item_status(
        item_id,
        UpdateQueueItemStatusRequest(queue_status="ready_for_workflow"),
        actor_user_id=None,
        actor_role="sales",
    )
    assert updated.item.queue_status == "ready_for_workflow"


async def test_ungueltiger_status_uebergang_wird_abgelehnt():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results)
    built = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )
    item_id = built.items[0].id

    # queued -> approved is not a permitted direct transition.
    with pytest.raises(InvalidOutreachQueueStatusTransitionError):
        await service.update_queue_item_status(
            item_id,
            UpdateQueueItemStatusRequest(queue_status="approved"),
            actor_user_id=None,
            actor_role="sales",
        )


async def test_rejected_kann_nicht_zu_external_draft_created_wechseln():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results)
    built = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )
    item_id = built.items[0].id
    for target in ("ready_for_workflow", "workflow_prepared", "draft_created", "review_pending"):
        await service.update_queue_item_status(
            item_id,
            UpdateQueueItemStatusRequest(queue_status=target),
            actor_user_id=None,
            actor_role="sales",
        )
    await service.update_queue_item_status(
        item_id,
        UpdateQueueItemStatusRequest(queue_status="rejected"),
        actor_user_id=None,
        actor_role="sales",
    )

    with pytest.raises(InvalidOutreachQueueStatusTransitionError):
        await service.update_queue_item_status(
            item_id,
            UpdateQueueItemStatusRequest(queue_status="external_draft_created"),
            actor_user_id=None,
            actor_role="sales",
        )


async def test_blocked_kann_nicht_ohne_erneute_pruefung_zu_ready_for_workflow_wechseln():
    service, companies, leads, results, compliance = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results, domain="blocked2.example.com")
    await compliance.create_entry(
        CreateDoNotContactRequest(domain="blocked2.example.com", reason="opted out"),
        created_by_user_id=None,
    )
    built = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )
    item_id = built.items[0].id
    assert built.items[0].queue_status == "blocked"

    with pytest.raises(OutreachQueueItemBlockedError):
        await service.update_queue_item_status(
            item_id,
            UpdateQueueItemStatusRequest(queue_status="ready_for_workflow"),
            actor_user_id=None,
            actor_role="sales",
        )


async def test_kein_sent_status_moeglich():
    with pytest.raises(Exception):
        UpdateQueueItemStatusRequest(queue_status="sent")  # type: ignore[arg-type]


async def test_unbekanntes_queue_item_wirft_not_found():
    service, *_ = _build_wiring()
    with pytest.raises(OutreachQueueItemNotFoundError):
        await service.get_queue_item(uuid.uuid4())


# -- workflow preparation ------------------------------------------------------------


async def test_einzelnes_queue_item_kann_workflow_vorbereiten():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results)
    built = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )
    item_id = built.items[0].id

    response = await service.prepare_queue_item_workflow(
        item_id,
        PrepareQueueItemWorkflowRequest(),
        actor_user_id=None,
        actor_role="sales",
    )

    assert response.blocked is False
    assert response.workflow_id is not None
    assert response.item.workflow_run_id is not None
    assert response.item.queue_status in ("workflow_prepared", "review_pending")


async def test_workflow_preparation_prueft_do_not_contact():
    service, companies, leads, results, compliance = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results, domain="dnc3.example.com")
    built = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )
    item_id = built.items[0].id
    # Opt-out is added after the item was queued clear — preparation must
    # re-check, not trust the queue-build-time status.
    await compliance.create_entry(
        CreateDoNotContactRequest(domain="dnc3.example.com", reason="opted out"),
        created_by_user_id=None,
    )

    response = await service.prepare_queue_item_workflow(
        item_id,
        PrepareQueueItemWorkflowRequest(),
        actor_user_id=None,
        actor_role="sales",
    )

    assert response.blocked is True
    assert response.item.queue_status == "blocked"


async def test_bereits_blockiertes_item_kann_nicht_vorbereitet_werden():
    service, companies, leads, results, compliance = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results, domain="dnc4.example.com")
    await compliance.create_entry(
        CreateDoNotContactRequest(domain="dnc4.example.com", reason="opted out"),
        created_by_user_id=None,
    )
    built = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )
    item_id = built.items[0].id

    with pytest.raises(OutreachQueueItemBlockedError):
        await service.prepare_queue_item_workflow(
            item_id,
            PrepareQueueItemWorkflowRequest(),
            actor_user_id=None,
            actor_role="sales",
        )


# -- batch preparation --------------------------------------------------------------


async def test_batch_preparation_respektiert_max_items():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    result_ids = []
    for i in range(3):
        _, _, result = await _seed_lead_and_result(
            companies, leads, results, domain=f"batch{i}.example.com"
        )
        result_ids.append(result.id)
    built = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=result_ids),
        actor_user_id=None,
        actor_role="sales",
    )
    assert len(built.items) == 3

    response = await service.prepare_batch(
        campaign.id,
        PrepareQueueBatchRequest(max_items=2),
        actor_user_id=None,
        actor_role="sales",
    )

    assert response.total_requested == 2
    assert response.prepared_count == 2


async def test_batch_preparation_erstellt_keine_externen_drafts():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results)
    built = await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )

    response = await service.prepare_batch(
        campaign.id,
        PrepareQueueBatchRequest(),
        actor_user_id=None,
        actor_role="sales",
    )

    assert response.prepared_count == 1
    for item in response.items:
        assert item.queue_status != "external_draft_created"
        assert item.external_draft_id is None


# -- dashboard --------------------------------------------------------------------


async def test_dashboard_funktioniert():
    service, companies, leads, results, _ = _build_wiring()
    campaign = await _create_campaign(service)
    _, _, result = await _seed_lead_and_result(companies, leads, results)
    await service.build_queue(
        campaign.id,
        BuildOutreachQueueRequest(qualification_result_ids=[result.id]),
        actor_user_id=None,
        actor_role="sales",
    )

    dashboard = await service.get_dashboard()
    assert dashboard.total_queued == 1
    assert len(dashboard.campaigns) == 1


async def test_status_endpoint_meldet_auto_create_external_drafts_immer_false():
    service, *_ = _build_wiring()
    status = await service.get_status()
    assert status.auto_create_external_drafts is False
