"""Tests for Data Export: cross-entity search by email/domain/name.

Covers: matching by domain, no secrets/tokens/api keys ever present in the
export, and an audit event being recorded for every export.
"""

import uuid

from backend.application.compliance.data_export_schemas import DataExportRequest
from backend.domain.entities.company import Company
from backend.domain.entities.contact import Contact
from tests.conftest import (
    FakeAuditLogRepository,
    FakeCompanyRepository,
    FakeContactRepository,
    build_fake_audit_log_service,
    build_fake_data_export_service,
)


async def test_export_findet_treffer_ueber_domain():
    companies = FakeCompanyRepository()
    contacts = FakeContactRepository()
    company = await companies.create(Company(name="Acme GmbH", domain="acme.example"))
    await contacts.create(
        Contact(
            company_id=company.id,
            first_name="Henrik",
            last_name="Hensen",
            email="henrik@acme.example",
        )
    )
    service = build_fake_data_export_service(companies=companies, contacts=contacts)

    result = await service.export(
        DataExportRequest(domain="acme.example"),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert len(result.companies) == 1
    assert len(result.leads) == 1
    assert result.leads[0]["email"] == "henrik@acme.example"


async def test_export_ohne_treffer_ist_leer():
    service = build_fake_data_export_service()
    result = await service.export(
        DataExportRequest(domain="unknown.example"),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert result.companies == []
    assert result.leads == []


async def test_export_enthaelt_keine_secrets():
    companies = FakeCompanyRepository()
    contacts = FakeContactRepository()
    company = await companies.create(Company(name="Acme GmbH", domain="acme.example"))
    await contacts.create(
        Contact(
            company_id=company.id,
            first_name="Henrik",
            last_name="Hensen",
            email="henrik@acme.example",
            phone="+49123456",
        )
    )
    service = build_fake_data_export_service(companies=companies, contacts=contacts)
    result = await service.export(
        DataExportRequest(domain="acme.example"),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    dumped = result.model_dump_json().lower()
    for forbidden in ("token", "secret", "api_key", "client_secret", "password"):
        assert forbidden not in dumped


async def test_export_schreibt_audit_event():
    audit_logs = FakeAuditLogRepository()
    audit = build_fake_audit_log_service(audit_logs=audit_logs)
    service = build_fake_data_export_service(audit=audit, audit_logs=audit_logs)

    await service.export(
        DataExportRequest(email="someone@example.com"),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    actions = {e.action for e in await audit_logs.list_filtered(limit=100)}
    assert "data_export_executed" in actions
