"""Tests for Controlled Outreach Dispatch.

Covers: safe config defaults, readiness checks (including every blocker),
external draft creation in mock mode, manual-send simulation restricted to
the mock provider, real send staying disabled unless explicitly enabled,
compliance acknowledgement and final confirmation being mandatory gates,
audit logging, the business-level volume cap, queue item status updates,
and the standing rule that no secret/token ever appears on a dispatch
record.
"""

import uuid

import pytest

from backend.application.compliance.schemas import CreateDoNotContactRequest
from backend.application.outreach.dispatch_schemas import (
    CancelDispatchRequest,
    ConfirmDispatchRequest,
    CreateDispatchRequest,
    DispatchComplianceAckRequest,
    DispatchReadinessCheckRequest,
)
from backend.domain.entities.company import Company
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.entities.lead_candidate import LeadCandidate
from backend.domain.entities.outreach_queue_item import OutreachQueueItem
from backend.domain.enums import EmailDraftReviewStatus
from backend.domain.exceptions import (
    OutreachDispatchBlockedError,
    OutreachDispatchNotFoundError,
    OutreachDispatchNotReadyError,
)
from backend.shared.config import Settings
from tests.conftest import (
    FakeCompanyRepository,
    FakeEmailDraftRepository,
    FakeLeadCandidateRepository,
    FakeLeadRepository,
    FakeOutreachDispatchRepository,
    FakeOutreachQueueItemRepository,
    build_fake_compliance_service,
    build_fake_outreach_dispatch_service,
)

_FULL_ACK = DispatchComplianceAckRequest(
    contact_permission_confirmed=True,
    do_not_contact_confirmed=True,
    human_review_confirmed=True,
    draft_or_controlled_send_confirmed=True,
    legal_responsibility_confirmed=True,
)


def _build_wiring(settings: Settings | None = None):
    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    lead_candidates = FakeLeadCandidateRepository()
    email_drafts = FakeEmailDraftRepository()
    queue_items = FakeOutreachQueueItemRepository()
    dispatches = FakeOutreachDispatchRepository()
    compliance = build_fake_compliance_service()
    service = build_fake_outreach_dispatch_service(
        dispatches=dispatches,
        queue_items=queue_items,
        email_drafts=email_drafts,
        companies=companies,
        lead_candidates=lead_candidates,
        compliance=compliance,
        settings=settings,
    )
    return service, queue_items, email_drafts, companies, lead_candidates, compliance, dispatches


async def _seed_ready_item(
    queue_items,
    email_drafts,
    companies,
    lead_candidates,
    *,
    domain: str = "acme.example.com",
    review_status: EmailDraftReviewStatus = EmailDraftReviewStatus.APPROVED,
    recipient_email: str = "info@acme.example.com",
    queue_status: str = "approved",
) -> OutreachQueueItem:
    company = await companies.create(Company(name="Acme GmbH", domain=domain, industry="Logistics"))
    candidate = await lead_candidates.create(
        LeadCandidate(
            sourcing_run_id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            company_name=company.name,
            company_domain=domain,
            public_contact_email=recipient_email,
        )
    )
    draft = await email_drafts.create(
        EmailDraft(
            company_id=company.id,
            email_body="This is the full email body used only for the workflow draft.",
            subject_lines=["Quick question about your fleet ops"],
            review_status=review_status,
        )
    )
    item = await queue_items.create(
        OutreachQueueItem(
            campaign_id=uuid.uuid4(),
            company_id=company.id,
            lead_candidate_id=candidate.id,
            email_draft_id=draft.id,
            queue_status=queue_status,
            qualification_score=90,
            qualification_level="excellent",
            recommended_outreach_angle="Fleet visibility angle.",
        )
    )
    return item


# -- config defaults ----------------------------------------------------------------


def test_dispatch_config_defaults_sind_safe():
    settings = Settings()
    assert settings.outreach_dispatch_enabled is True
    assert settings.outreach_dispatch_mode == "draft_only"
    assert settings.outreach_dispatch_provider == "mock"
    assert settings.outreach_dispatch_enable_real_send is False
    assert settings.outreach_dispatch_require_final_confirmation is True
    assert settings.outreach_dispatch_require_approved_review is True
    assert settings.outreach_dispatch_require_do_not_contact_check is True
    assert settings.outreach_dispatch_require_compliance_ack is True
    assert settings.outreach_dispatch_max_per_day == 25
    assert settings.outreach_dispatch_max_per_hour == 10


def test_dispatch_mode_default_ist_draft_only():
    assert Settings().outreach_dispatch_mode == "draft_only"


def test_real_send_default_ist_false():
    assert Settings().outreach_dispatch_enable_real_send is False


# -- readiness ------------------------------------------------------------------


async def test_readiness_check_funktioniert():
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring()
    item = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates)

    readiness = await service.check_readiness(
        item.id, DispatchReadinessCheckRequest(), actor_user_id=uuid.uuid4()
    )
    assert readiness.checks.email_draft_exists is True
    assert readiness.checks.human_review_approved is True
    assert readiness.checks.queue_item_allowed is True


async def test_readiness_blockiert_bei_do_not_contact():
    service, queue_items, email_drafts, companies, lead_candidates, compliance, _dispatches = _build_wiring()
    item = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates, domain="blocked.example.com")
    await compliance.create_entry(
        CreateDoNotContactRequest(domain="blocked.example.com", reason="opted out"),
        created_by_user_id=None,
    )

    readiness = await service.check_readiness(
        item.id, DispatchReadinessCheckRequest(), actor_user_id=uuid.uuid4()
    )
    assert readiness.checks.do_not_contact_passed is False
    assert readiness.is_ready is False
    assert any("do-not-contact" in b.lower() for b in readiness.blockers)


async def test_readiness_blockiert_bei_fehlender_review_approval():
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring()
    item = await _seed_ready_item(
        queue_items,
        email_drafts,
        companies,
        lead_candidates,
        review_status=EmailDraftReviewStatus.NEEDS_REVIEW,
    )

    readiness = await service.check_readiness(
        item.id, DispatchReadinessCheckRequest(), actor_user_id=uuid.uuid4()
    )
    assert readiness.checks.human_review_approved is False
    assert readiness.is_ready is False


async def test_readiness_blockiert_bei_fehlendem_email_draft():
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring()
    company = await companies.create(Company(name="NoDraft Inc", domain="nodraft.example.com"))
    item = await queue_items.create(
        OutreachQueueItem(
            campaign_id=uuid.uuid4(),
            company_id=company.id,
            queue_status="approved",
            qualification_score=80,
        )
    )

    readiness = await service.check_readiness(
        item.id, DispatchReadinessCheckRequest(), actor_user_id=uuid.uuid4()
    )
    assert readiness.checks.email_draft_exists is False
    assert readiness.is_ready is False


async def test_readiness_blockiert_bei_blocked_queue_item():
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring()
    item = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates, queue_status="blocked")

    readiness = await service.check_readiness(
        item.id, DispatchReadinessCheckRequest(), actor_user_id=uuid.uuid4()
    )
    assert readiness.checks.queue_item_allowed is False
    assert readiness.is_ready is False


async def test_unbekanntes_queue_item_bei_readiness_wirft_not_found():
    from backend.domain.exceptions import OutreachQueueItemNotFoundError

    service, *_ = _build_wiring()
    with pytest.raises(OutreachQueueItemNotFoundError):
        await service.check_readiness(
            uuid.uuid4(), DispatchReadinessCheckRequest(), actor_user_id=uuid.uuid4()
        )


# -- create / ack / confirm: draft_only ----------------------------------------------


async def test_dispatch_erstellt_externen_draft_im_mock_mode():
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring()
    item = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates)
    actor = uuid.uuid4()

    created = await service.create_dispatch(
        item.id, CreateDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )
    assert created.readiness.is_ready is True
    assert created.dispatch.dispatch_status == "pending"

    acked = await service.acknowledge_compliance(
        created.dispatch.id, _FULL_ACK, actor_user_id=actor, actor_role="sales"
    )
    assert acked.dispatch.dispatch_status == "ready"

    confirmed = await service.confirm(
        created.dispatch.id, ConfirmDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )
    assert confirmed.dispatch.dispatch_status == "external_draft_created"
    assert confirmed.dispatch.provider_draft_id is not None

    updated_item = await queue_items.get_by_id(item.id)
    assert updated_item is not None
    assert updated_item.queue_status == "external_draft_created"


async def test_final_confirmation_ist_erforderlich():
    """Confirming twice must not silently no-op — a completed dispatch is
    terminal and a second confirm attempt is rejected."""
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring()
    item = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates)
    actor = uuid.uuid4()

    created = await service.create_dispatch(
        item.id, CreateDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )
    await service.acknowledge_compliance(
        created.dispatch.id, _FULL_ACK, actor_user_id=actor, actor_role="sales"
    )
    await service.confirm(
        created.dispatch.id, ConfirmDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )

    with pytest.raises(OutreachDispatchNotReadyError):
        await service.confirm(
            created.dispatch.id, ConfirmDispatchRequest(), actor_user_id=actor, actor_role="sales"
        )


async def test_compliance_ack_ist_erforderlich():
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring()
    item = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates)
    actor = uuid.uuid4()

    created = await service.create_dispatch(
        item.id, CreateDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )
    # No compliance-ack call — confirm must refuse to execute.
    with pytest.raises(OutreachDispatchBlockedError):
        await service.confirm(
            created.dispatch.id, ConfirmDispatchRequest(), actor_user_id=actor, actor_role="sales"
        )
    reloaded = await service.get_dispatch(created.dispatch.id)
    assert reloaded.dispatch_status == "blocked"


async def test_compliance_ack_verlangt_alle_statements():
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring()
    item = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates)
    actor = uuid.uuid4()
    created = await service.create_dispatch(
        item.id, CreateDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )
    incomplete = DispatchComplianceAckRequest(
        contact_permission_confirmed=True,
        do_not_contact_confirmed=True,
        human_review_confirmed=True,
        draft_or_controlled_send_confirmed=True,
        legal_responsibility_confirmed=False,
    )
    with pytest.raises(OutreachDispatchBlockedError):
        await service.acknowledge_compliance(
            created.dispatch.id, incomplete, actor_user_id=actor, actor_role="sales"
        )


# -- manual send ------------------------------------------------------------------


async def test_manual_send_simuliert_nur_im_mock_mode():
    settings = Settings(
        OUTREACH_DISPATCH_MODE="manual_send", OUTREACH_DISPATCH_ENABLE_REAL_SEND=True
    )
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring(settings)
    item = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates)
    actor = uuid.uuid4()

    created = await service.create_dispatch(
        item.id, CreateDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )
    assert created.dispatch.dispatch_mode == "manual_send"
    await service.acknowledge_compliance(
        created.dispatch.id, _FULL_ACK, actor_user_id=actor, actor_role="sales"
    )
    confirmed = await service.confirm(
        created.dispatch.id, ConfirmDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )
    assert confirmed.dispatch.dispatch_status == "sent_manually_confirmed"
    assert confirmed.dispatch.provider_message_id is not None
    assert confirmed.dispatch.provider_message_id.startswith("mock-msg-")

    updated_item = await queue_items.get_by_id(item.id)
    assert updated_item.queue_status == "sent_manually_confirmed"


async def test_real_send_wird_nicht_ausgefuehrt_wenn_deaktiviert():
    settings = Settings(
        OUTREACH_DISPATCH_MODE="manual_send", OUTREACH_DISPATCH_ENABLE_REAL_SEND=False
    )
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring(settings)
    item = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates)
    actor = uuid.uuid4()

    created = await service.create_dispatch(
        item.id, CreateDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )
    await service.acknowledge_compliance(
        created.dispatch.id, _FULL_ACK, actor_user_id=actor, actor_role="sales"
    )
    # Real send disabled: manual_send confirmation is never allowed.
    with pytest.raises(OutreachDispatchBlockedError):
        await service.confirm(
            created.dispatch.id, ConfirmDispatchRequest(), actor_user_id=actor, actor_role="sales"
        )
    reloaded = await service.get_dispatch(created.dispatch.id)
    assert reloaded.dispatch_status == "blocked"

    updated_item = await queue_items.get_by_id(item.id)
    assert updated_item.queue_status == "approved"


async def test_real_provider_gmail_sendet_niemals_wirklich():
    """Even with a fully-configured, real-send-enabled Gmail provider, the
    provider itself must refuse to send — no send scope is ever requested
    anywhere in this codebase, so this is a unit-level guarantee on the
    provider class itself, independent of the readiness/config gates."""
    from backend.application.integrations.email_draft_integration_service import (
        EmailDraftIntegrationService,
    )
    from backend.infrastructure.dispatch.real_provider import GmailDispatchProvider
    from tests.conftest import (
        FakeCompanyRepository,
        FakeContactRepository,
        FakeEmailProviderConnectionRepository,
        FakeExternalEmailDraftRepository,
        FakeWorkflowRunRepository,
    )

    settings = Settings(
        GOOGLE_CLIENT_ID="test-client-id",
        GOOGLE_CLIENT_SECRET="test-client-secret",
        EMAIL_TOKEN_ENCRYPTION_KEY="0" * 32,
    )
    email_draft_integration = EmailDraftIntegrationService(
        connections=FakeEmailProviderConnectionRepository(),
        external_drafts=FakeExternalEmailDraftRepository(),
        email_drafts=FakeEmailDraftRepository(),
        companies=FakeCompanyRepository(),
        workflow_runs=FakeWorkflowRunRepository(),
        contacts=FakeContactRepository(),
        compliance=build_fake_compliance_service(),
        settings=settings,
    )
    provider = GmailDispatchProvider(
        email_draft_integration, FakeEmailProviderConnectionRepository(), settings
    )

    status = await provider.get_provider_status(uuid.uuid4())
    assert status.configured is True
    assert status.supports_manual_send is False

    result = await provider.send_manual_confirmed_message(
        user_id=uuid.uuid4(), email_draft_id=uuid.uuid4(), dispatch_id=uuid.uuid4()
    )
    assert result.blocked is True
    assert result.status == "blocked"
    assert "send scope" in result.message.lower()


# -- cancel -------------------------------------------------------------------------


async def test_dispatch_kann_cancelled_werden():
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring()
    item = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates)
    actor = uuid.uuid4()
    created = await service.create_dispatch(
        item.id, CreateDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )
    cancelled = await service.cancel(
        created.dispatch.id,
        CancelDispatchRequest(reason="Changed my mind"),
        actor_user_id=actor,
        actor_role="sales",
    )
    assert cancelled.dispatch.dispatch_status == "cancelled"


async def test_unbekannter_dispatch_wirft_not_found():
    service, *_ = _build_wiring()
    with pytest.raises(OutreachDispatchNotFoundError):
        await service.get_dispatch(uuid.uuid4())


# -- rate limit / volume cap ----------------------------------------------------------


async def test_dispatch_respektiert_volumen_limit():
    settings = Settings(OUTREACH_DISPATCH_MAX_PER_HOUR=1)
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring(settings)
    actor = uuid.uuid4()

    item1 = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates, domain="one.example.com")
    item2 = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates, domain="two.example.com")

    await service.create_dispatch(
        item1.id, CreateDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )
    readiness2 = await service.check_readiness(
        item2.id, DispatchReadinessCheckRequest(), actor_user_id=actor
    )
    assert readiness2.checks.rate_limit_ok is False
    assert readiness2.is_ready is False


# -- audit --------------------------------------------------------------------------


async def test_dispatch_speichert_audit_logs():
    from tests.conftest import FakeAuditLogRepository, build_fake_audit_log_service

    audit_repo = FakeAuditLogRepository()
    audit = build_fake_audit_log_service(audit_logs=audit_repo)
    queue_items = FakeOutreachQueueItemRepository()
    email_drafts = FakeEmailDraftRepository()
    companies = FakeCompanyRepository()
    lead_candidates = FakeLeadCandidateRepository()
    service = build_fake_outreach_dispatch_service(
        queue_items=queue_items,
        email_drafts=email_drafts,
        companies=companies,
        lead_candidates=lead_candidates,
        audit=audit,
    )
    item = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates)
    actor = uuid.uuid4()

    await service.create_dispatch(
        item.id, CreateDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )
    logs = await audit_repo.list_filtered(limit=100)
    actions = {log.action for log in logs}
    assert "outreach_dispatch_created" in actions


# -- no secrets ----------------------------------------------------------------------


async def test_dispatch_zeigt_keine_secrets():
    service, queue_items, email_drafts, companies, lead_candidates, *_ = _build_wiring()
    item = await _seed_ready_item(queue_items, email_drafts, companies, lead_candidates)
    actor = uuid.uuid4()
    created = await service.create_dispatch(
        item.id, CreateDispatchRequest(), actor_user_id=actor, actor_role="sales"
    )
    dumped = created.dispatch.model_dump()
    serialized = str(dumped).lower()
    for forbidden in ("token", "secret", "api_key", "password"):
        assert forbidden not in serialized
    # Body preview must never be the full email body.
    assert created.dispatch.body_preview_snapshot is not None
    assert len(created.dispatch.body_preview_snapshot) <= 300
