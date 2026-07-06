"""Tests for the DoNotContactEntry domain entity and its schemas."""

import pytest
from pydantic import ValidationError

from backend.application.compliance.schemas import (
    CreateDoNotContactRequest,
    DoNotContactCheckRequest,
)
from backend.domain.entities.do_not_contact_entry import DoNotContactEntry


def test_entry_defaults_to_active_manual_source():
    entry = DoNotContactEntry(reason="Customer requested opt-out.")

    assert entry.is_active is True
    assert entry.source == "manual"
    assert entry.email is None
    assert entry.domain is None
    assert entry.company_name is None


def test_create_request_rejects_empty_target():
    with pytest.raises(ValidationError):
        CreateDoNotContactRequest(reason="No target given.")


def test_create_request_accepts_email_only():
    request = CreateDoNotContactRequest(email="user@example.com", reason="Opted out.")
    assert request.email == "user@example.com"


def test_create_request_accepts_domain_only():
    request = CreateDoNotContactRequest(domain="example.com", reason="Opted out.")
    assert request.domain == "example.com"


def test_create_request_accepts_company_name_only():
    request = CreateDoNotContactRequest(company_name="Acme GmbH", reason="Opted out.")
    assert request.company_name == "Acme GmbH"


def test_check_request_rejects_empty_target():
    with pytest.raises(ValidationError):
        DoNotContactCheckRequest()
