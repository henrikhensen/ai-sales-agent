"""Tests for ReplyTrackingService using in-memory fakes, the mock reply
tracking provider, and the mock LLM provider — no real database, no
external calls, no OAuth, no real LLM usage.
"""

import uuid

from backend.domain.entities.company import Company
from backend.domain.entities.contact import Contact
from backend.domain.entities.lead import Lead
from backend.domain.enums import LeadSource
from tests.conftest import (
    FakeCompanyRepository,
    FakeContactRepository,
    FakeInteractionRepository,
    FakeLeadRepository,
    build_fake_compliance_service,
    build_fake_reply_tracking_service,
)


async def _seed_lead_with_contact(companies, leads, contacts, *, email: str):
    company = await companies.create(Company(name="Acme GmbH", domain="acme.example"))
    lead = await leads.create(Lead(company_id=company.id, source=LeadSource.OUTBOUND))
    await contacts.create(
        Contact(company_id=company.id, first_name="Jane", last_name="Doe", email=email)
    )
    return company, lead


async def test_sync_replies_for_lead_stores_new_reply():
    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    contacts = FakeContactRepository()
    company, lead = await _seed_lead_with_contact(
        companies, leads, contacts, email="jane@acme.example"
    )
    service = build_fake_reply_tracking_service(
        companies=companies, leads=leads, contacts=contacts
    )

    result = await service.sync_replies_for_lead(uuid.uuid4(), lead.id)

    assert result.status == "mock_synced"
    assert result.new_count == 1
    assert result.duplicate_count == 0
    assert len(result.replies) == 1
    assert result.replies[0].lead_id == lead.id
    assert result.replies[0].company_id == company.id


async def test_sync_replies_for_lead_avoids_duplicates_on_second_sync():
    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    contacts = FakeContactRepository()
    _, lead = await _seed_lead_with_contact(
        companies, leads, contacts, email="jane@acme.example"
    )
    service = build_fake_reply_tracking_service(
        companies=companies, leads=leads, contacts=contacts
    )

    first = await service.sync_replies_for_lead(uuid.uuid4(), lead.id)
    second = await service.sync_replies_for_lead(uuid.uuid4(), lead.id)

    assert first.new_count == 1
    assert first.duplicate_count == 0
    assert second.new_count == 0
    assert second.duplicate_count == 1


async def test_body_preview_only_setting_discards_full_body_text():
    from backend.shared.config import Settings

    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    contacts = FakeContactRepository()
    _, lead = await _seed_lead_with_contact(
        companies, leads, contacts, email="jane@acme.example"
    )
    settings = Settings(
        REPLY_TRACKING_PROVIDER="mock", REPLY_TRACKING_STORE_BODY_PREVIEW_ONLY=True
    )
    service = build_fake_reply_tracking_service(
        companies=companies, leads=leads, contacts=contacts, settings=settings
    )

    result = await service.sync_replies_for_lead(uuid.uuid4(), lead.id)

    stored = result.replies[0]
    assert stored.body_preview is not None
    assert stored.body_text is None


async def test_full_body_is_stored_when_preview_only_is_disabled():
    from backend.shared.config import Settings

    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    contacts = FakeContactRepository()
    _, lead = await _seed_lead_with_contact(
        companies, leads, contacts, email="jane@acme.example"
    )
    settings = Settings(
        REPLY_TRACKING_PROVIDER="mock", REPLY_TRACKING_STORE_BODY_PREVIEW_ONLY=False
    )
    service = build_fake_reply_tracking_service(
        companies=companies, leads=leads, contacts=contacts, settings=settings
    )

    result = await service.sync_replies_for_lead(uuid.uuid4(), lead.id)

    assert result.replies[0].body_text is not None


async def test_reply_analysis_sets_a_category():
    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    contacts = FakeContactRepository()
    _, lead = await _seed_lead_with_contact(
        companies, leads, contacts, email="jane@acme.example"
    )
    service = build_fake_reply_tracking_service(
        companies=companies, leads=leads, contacts=contacts
    )

    result = await service.sync_replies_for_lead(uuid.uuid4(), lead.id)

    assert result.replies[0].reply_category is not None
    assert result.replies[0].detected_intent is not None
    assert result.replies[0].sentiment is not None
    assert result.replies[0].confidence_score is not None


async def test_unsubscribe_keyword_always_maps_to_unsubscribe_category():
    """Directly exercises the deterministic keyword override, independent
    of which mock sample a given email happens to rotate to."""
    from backend.application.integrations.reply_tracking_service import (
        _determine_reply_category,
    )
    from backend.domain.enums import ReplyCategory, ReplyIntent

    category = _determine_reply_category(
        ReplyIntent.INTERESTED, "Please unsubscribe me from this list."
    )
    assert category == ReplyCategory.UNSUBSCRIBE


async def test_unsubscribe_reply_creates_a_do_not_contact_entry_for_the_sender():
    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    contacts = FakeContactRepository()
    interactions = FakeInteractionRepository()
    compliance = build_fake_compliance_service()

    company, lead = await _seed_lead_with_contact(
        companies, leads, contacts, email="opt-out-sample@acme.example"
    )
    service = build_fake_reply_tracking_service(
        companies=companies,
        leads=leads,
        contacts=contacts,
        interactions=interactions,
        compliance=compliance,
    )

    # The mock provider rotates through 6 sample bodies deterministically
    # per email address; probing several addresses reliably hits the
    # unsubscribe-worded sample at least once without depending on which
    # exact address maps to it.
    found_signal = False
    blocked_email = None
    for i in range(12):
        email = f"probe{i}@acme.example"
        await contacts.create(
            Contact(company_id=company.id, first_name="P", last_name=str(i), email=email)
        )
        result = await service.sync_replies_for_lead(uuid.uuid4(), lead.id)
        for reply in result.replies:
            if reply.reply_category == "unsubscribe":
                found_signal = True
                blocked_email = reply.from_email
    assert found_signal

    check = await compliance.check(email=blocked_email)
    assert check.is_blocked is True
    assert check.matched_by == "email"
    assert check.reason is not None and "unsubscribe" in check.reason.lower()

    # A matching do-not-contact-signal Interaction was recorded for audit.
    recorded = await interactions.list_by_lead(lead.id)
    assert any(i.status == "do_not_contact_signal_detected" for i in recorded)


async def test_pipeline_recommendation_is_computed_not_applied():
    from backend.application.integrations.reply_tracking_service import (
        _recommended_pipeline_status,
    )

    assert _recommended_pipeline_status("interested") == "in_review"
    assert _recommended_pipeline_status("meeting_request") == "in_review"
    assert _recommended_pipeline_status("needs_more_info") == "in_review"
    assert _recommended_pipeline_status("not_interested") == "rejected"
    assert _recommended_pipeline_status("unsubscribe") == "archived"
    assert _recommended_pipeline_status("out_of_office") == "research_completed"
    assert _recommended_pipeline_status("unknown") == "research_completed"
    assert _recommended_pipeline_status(None) is None


async def test_compliance_warning_only_set_for_unsubscribe():
    from backend.application.integrations.reply_tracking_service import (
        _compliance_warning,
    )

    assert _compliance_warning("unsubscribe") is not None
    assert _compliance_warning("interested") is None
    assert _compliance_warning(None) is None


async def test_sync_replies_for_lead_raises_for_unknown_lead():
    from backend.domain.exceptions import LeadNotFoundError

    import pytest

    service = build_fake_reply_tracking_service()
    with pytest.raises(LeadNotFoundError):
        await service.sync_replies_for_lead(uuid.uuid4(), uuid.uuid4())


async def test_sync_records_an_interaction_for_the_lead():
    companies = FakeCompanyRepository()
    leads = FakeLeadRepository()
    contacts = FakeContactRepository()
    interactions = FakeInteractionRepository()
    _, lead = await _seed_lead_with_contact(
        companies, leads, contacts, email="jane@acme.example"
    )
    service = build_fake_reply_tracking_service(
        companies=companies, leads=leads, contacts=contacts, interactions=interactions
    )

    await service.sync_replies_for_lead(uuid.uuid4(), lead.id)

    recorded = await interactions.list_by_lead(lead.id)
    assert any(i.status == "replies_synced" for i in recorded)


async def test_get_status_reports_mock_active_by_default():
    service = build_fake_reply_tracking_service()
    status = await service.get_status(uuid.uuid4())

    assert status.active_provider == "mock"
    assert status.safe_mode is True
    assert status.real_reads_enabled is False
