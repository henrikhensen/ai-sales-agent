"""Tests for EmailDraftIntegrationService using in-memory fakes and the
mock email draft provider — no real database, no external calls, no OAuth.
"""

import uuid

import pytest

from backend.application.compliance.schemas import CreateDoNotContactRequest
from backend.domain.entities.company import Company
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.enums import EmailDraftReviewStatus, ExternalDraftProviderStatus
from backend.domain.exceptions import EmailDraftNotFoundError
from tests.conftest import (
    FakeCompanyRepository,
    FakeEmailDraftRepository,
    build_fake_compliance_service,
    build_fake_email_draft_integration_service,
)


async def _seed_approved_draft(email_drafts: FakeEmailDraftRepository, **overrides):
    defaults = dict(
        company_id=uuid.uuid4(),
        email_body="Hallo,\n\nGrüße",
        review_status=EmailDraftReviewStatus.APPROVED,
    )
    defaults.update(overrides)
    return await email_drafts.create(EmailDraft(**defaults))


async def test_create_external_draft_raises_for_unknown_draft():
    service = build_fake_email_draft_integration_service()
    with pytest.raises(EmailDraftNotFoundError):
        await service.create_external_draft(uuid.uuid4(), uuid.uuid4())


async def test_create_external_draft_blocks_when_not_approved():
    email_drafts = FakeEmailDraftRepository()
    draft = await _seed_approved_draft(
        email_drafts, review_status=EmailDraftReviewStatus.NEEDS_REVIEW
    )
    service = build_fake_email_draft_integration_service(email_drafts=email_drafts)

    result = await service.create_external_draft(uuid.uuid4(), draft.id)

    assert result.blocked is True
    assert result.block_reason == "review_not_approved"
    assert result.external_draft.provider_status == "blocked"


async def test_create_external_draft_blocks_when_rejected():
    email_drafts = FakeEmailDraftRepository()
    draft = await _seed_approved_draft(
        email_drafts, review_status=EmailDraftReviewStatus.REJECTED
    )
    service = build_fake_email_draft_integration_service(email_drafts=email_drafts)

    result = await service.create_external_draft(uuid.uuid4(), draft.id)

    assert result.blocked is True
    assert result.block_reason == "review_not_approved"


async def test_create_external_draft_blocks_on_do_not_contact_match():
    email_drafts = FakeEmailDraftRepository()
    companies = FakeCompanyRepository()
    company = await companies.create(
        Company(name="Blocked GmbH", domain="blocked.example")
    )
    draft = await _seed_approved_draft(email_drafts, company_id=company.id)

    compliance = build_fake_compliance_service()
    await compliance.create_entry(
        CreateDoNotContactRequest(company_name="Blocked GmbH", reason="Opt-out"),
        created_by_user_id=None,
    )
    service = build_fake_email_draft_integration_service(
        email_drafts=email_drafts, companies=companies, compliance=compliance
    )

    result = await service.create_external_draft(uuid.uuid4(), draft.id)

    assert result.blocked is True
    assert result.block_reason == "do_not_contact"
    assert result.external_draft.provider_status == "blocked"


async def test_do_not_contact_block_never_calls_the_provider(monkeypatch):
    email_drafts = FakeEmailDraftRepository()
    companies = FakeCompanyRepository()
    company = await companies.create(
        Company(name="Blocked GmbH", domain="blocked.example")
    )
    draft = await _seed_approved_draft(email_drafts, company_id=company.id)

    compliance = build_fake_compliance_service()
    await compliance.create_entry(
        CreateDoNotContactRequest(company_name="Blocked GmbH", reason="Opt-out"),
        created_by_user_id=None,
    )
    service = build_fake_email_draft_integration_service(
        email_drafts=email_drafts, companies=companies, compliance=compliance
    )

    def _poison(*args, **kwargs):
        raise AssertionError(
            "create_email_draft_provider() must not be called when "
            "do-not-contact blocks the request"
        )

    monkeypatch.setattr(
        "backend.application.integrations.email_draft_integration_service."
        "create_email_draft_provider",
        _poison,
    )

    result = await service.create_external_draft(uuid.uuid4(), draft.id)
    assert result.blocked is True
    assert result.block_reason == "do_not_contact"


async def test_create_external_draft_succeeds_via_mock_provider():
    email_drafts = FakeEmailDraftRepository()
    draft = await _seed_approved_draft(email_drafts)
    service = build_fake_email_draft_integration_service(email_drafts=email_drafts)
    user_id = uuid.uuid4()

    result = await service.create_external_draft(user_id, draft.id)

    assert result.blocked is False
    assert result.external_draft.provider == "mock"
    assert result.external_draft.provider_status == "mock_created"
    assert result.external_draft.provider_draft_id is not None
    assert result.external_draft.provider_draft_url is not None
    assert result.external_draft.created_by_user_id == user_id
    assert result.external_draft.provider_status != "sent"


async def test_provider_status_is_never_sent_across_all_outcomes():
    email_drafts = FakeEmailDraftRepository()
    approved = await _seed_approved_draft(email_drafts)
    needs_review = await _seed_approved_draft(
        email_drafts, review_status=EmailDraftReviewStatus.NEEDS_REVIEW
    )
    service = build_fake_email_draft_integration_service(email_drafts=email_drafts)

    ok_result = await service.create_external_draft(uuid.uuid4(), approved.id)
    blocked_result = await service.create_external_draft(uuid.uuid4(), needs_review.id)

    assert ok_result.external_draft.provider_status != "sent"
    assert blocked_result.external_draft.provider_status != "sent"


async def test_get_external_draft_status_reports_not_created_yet():
    email_drafts = FakeEmailDraftRepository()
    draft = await _seed_approved_draft(email_drafts)
    service = build_fake_email_draft_integration_service(email_drafts=email_drafts)

    status = await service.get_external_draft_status(draft.id)

    assert status.exists is False
    assert status.external_draft is None


async def test_get_external_draft_status_reports_created_draft():
    email_drafts = FakeEmailDraftRepository()
    draft = await _seed_approved_draft(email_drafts)
    service = build_fake_email_draft_integration_service(email_drafts=email_drafts)
    await service.create_external_draft(uuid.uuid4(), draft.id)

    status = await service.get_external_draft_status(draft.id)

    assert status.exists is True
    assert status.external_draft.provider_status == "mock_created"


async def test_get_external_draft_status_raises_for_unknown_draft():
    service = build_fake_email_draft_integration_service()
    with pytest.raises(EmailDraftNotFoundError):
        await service.get_external_draft_status(uuid.uuid4())


async def test_get_status_reports_mock_active_by_default():
    service = build_fake_email_draft_integration_service()
    status = await service.get_status(uuid.uuid4())

    assert status.active_provider == "mock"
    assert status.safe_mode is True
    assert status.real_drafts_enabled is False


async def test_list_providers_includes_mock_gmail_outlook():
    service = build_fake_email_draft_integration_service()
    result = await service.list_providers(uuid.uuid4())

    names = {item.provider for item in result.items}
    assert names == {"mock", "gmail", "outlook"}
    mock_info = next(item for item in result.items if item.provider == "mock")
    assert mock_info.is_active_provider is True
    assert mock_info.requires_oauth is False
