"""Tests for DoNotContactService using the in-memory FakeDoNotContactRepository —
no real database, no external calls of any kind.
"""

import uuid

import pytest

from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.compliance.schemas import (
    CreateDoNotContactRequest,
    UpdateDoNotContactRequest,
)
from backend.domain.exceptions import DoNotContactEntryNotFoundError
from tests.conftest import FakeDoNotContactRepository


def _service() -> DoNotContactService:
    return DoNotContactService(FakeDoNotContactRepository())


async def test_create_entry_stores_email_lowercase():
    service = _service()
    created = await service.create_entry(
        CreateDoNotContactRequest(email="User@Example.COM", reason="Opt-out"),
        created_by_user_id=None,
    )
    assert created.email == "user@example.com"


async def test_create_entry_stores_domain_lowercase():
    service = _service()
    created = await service.create_entry(
        CreateDoNotContactRequest(domain="Example.COM", reason="Opt-out"),
        created_by_user_id=None,
    )
    assert created.domain == "example.com"


async def test_create_entry_keeps_company_name_display_casing():
    service = _service()
    created = await service.create_entry(
        CreateDoNotContactRequest(company_name="  Acme GmbH  ", reason="Opt-out"),
        created_by_user_id=None,
    )
    assert created.company_name == "Acme GmbH"


async def test_create_entry_defaults_active_and_manual_source():
    service = _service()
    created = await service.create_entry(
        CreateDoNotContactRequest(email="user@example.com", reason="Opt-out"),
        created_by_user_id=None,
    )
    assert created.is_active is True
    assert created.source == "manual"


async def test_list_entries_returns_created_entry():
    service = _service()
    await service.create_entry(
        CreateDoNotContactRequest(email="user@example.com", reason="Opt-out"),
        created_by_user_id=None,
    )
    listing = await service.list_entries()
    assert len(listing.items) == 1
    assert listing.items[0].email == "user@example.com"


async def test_update_entry_changes_reason_only():
    service = _service()
    created = await service.create_entry(
        CreateDoNotContactRequest(email="user@example.com", reason="Original reason"),
        created_by_user_id=None,
    )
    updated = await service.update_entry(
        created.id, UpdateDoNotContactRequest(reason="New reason")
    )
    assert updated.reason == "New reason"
    assert updated.email == "user@example.com"


async def test_update_entry_raises_for_unknown_id():
    service = _service()
    with pytest.raises(DoNotContactEntryNotFoundError):
        await service.update_entry(uuid.uuid4(), UpdateDoNotContactRequest(reason="x"))


async def test_deactivate_entry_sets_inactive():
    service = _service()
    created = await service.create_entry(
        CreateDoNotContactRequest(email="user@example.com", reason="Opt-out"),
        created_by_user_id=None,
    )
    deactivated = await service.deactivate_entry(created.id)
    assert deactivated.is_active is False


async def test_deactivate_entry_raises_for_unknown_id():
    service = _service()
    with pytest.raises(DoNotContactEntryNotFoundError):
        await service.deactivate_entry(uuid.uuid4())


# -- check() matching rules ----------------------------------------------------


async def test_check_email_match_blocks():
    service = _service()
    await service.create_entry(
        CreateDoNotContactRequest(email="blocked@example.com", reason="Opt-out"),
        created_by_user_id=None,
    )
    result = await service.check(email="Blocked@Example.com")
    assert result.is_blocked is True
    assert result.matched_by == "email"


async def test_check_domain_match_blocks_any_email_at_that_domain():
    service = _service()
    await service.create_entry(
        CreateDoNotContactRequest(domain="blocked.example", reason="Opt-out"),
        created_by_user_id=None,
    )
    result = await service.check(email="someone@blocked.example")
    assert result.is_blocked is True
    assert result.matched_by == "domain"


async def test_check_explicit_domain_match_blocks():
    service = _service()
    await service.create_entry(
        CreateDoNotContactRequest(domain="blocked.example", reason="Opt-out"),
        created_by_user_id=None,
    )
    result = await service.check(domain="blocked.example")
    assert result.is_blocked is True
    assert result.matched_by == "domain"


async def test_check_company_name_match_blocks():
    service = _service()
    await service.create_entry(
        CreateDoNotContactRequest(company_name="Acme GmbH", reason="Opt-out"),
        created_by_user_id=None,
    )
    result = await service.check(company_name="  acme   gmbh ")
    assert result.is_blocked is True
    assert result.matched_by == "company_name"


async def test_check_returns_not_blocked_when_no_match():
    service = _service()
    await service.create_entry(
        CreateDoNotContactRequest(email="blocked@example.com", reason="Opt-out"),
        created_by_user_id=None,
    )
    result = await service.check(email="fine@example.com", domain="fine.example")
    assert result.is_blocked is False
    assert result.matched_by is None


async def test_inactive_entry_never_blocks():
    service = _service()
    created = await service.create_entry(
        CreateDoNotContactRequest(email="user@example.com", reason="Opt-out"),
        created_by_user_id=None,
    )
    await service.deactivate_entry(created.id)

    result = await service.check(email="user@example.com")

    assert result.is_blocked is False


async def test_check_result_includes_reason_and_warning_message():
    service = _service()
    await service.create_entry(
        CreateDoNotContactRequest(
            email="blocked@example.com", reason="Legal opt-out request"
        ),
        created_by_user_id=None,
    )
    result = await service.check(email="blocked@example.com")

    assert result.reason == "Legal opt-out request"
    assert result.warning_message is not None
    assert "do-not-contact" in result.warning_message.lower()
