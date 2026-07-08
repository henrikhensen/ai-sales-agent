"""Tests for Data Retention: policies, dry-run, real runs, and per-entity
anonymization/delete behavior.

Covers: policy CRUD, dry runs never mutating data, anonymization removing
sensitive Contact/Reply fields and clearing/replacing an Email Draft body,
do-not-contact entries never being touched while still active, and audit
logs never being mutated (append-only by design).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.application.compliance.data_retention_schemas import (
    CreateDataRetentionPolicyRequest,
    RunDataRetentionPolicyRequest,
    UpdateDataRetentionPolicyRequest,
)
from backend.domain.entities.company import Company
from backend.domain.entities.contact import Contact
from backend.domain.entities.do_not_contact_entry import DoNotContactEntry
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.entities.reply import Reply
from backend.domain.enums import EmailProviderType
from backend.domain.exceptions import (
    DataRetentionPolicyNotFoundError,
    InvalidRetentionPolicyError,
    RetentionRunBlockedError,
)
from tests.conftest import (
    FakeAuditLogRepository,
    FakeCompanyRepository,
    FakeContactRepository,
    FakeDoNotContactRepository,
    FakeEmailDraftRepository,
    FakeReplyRepository,
    build_fake_audit_log_service,
    build_fake_data_retention_service,
)


def _old() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=2000)


async def test_policy_kann_erstellt_werden():
    service = build_fake_data_retention_service()
    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old Leads", entity_type="lead", retention_days=365
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert policy.name == "Old Leads"
    assert policy.action == "anonymize"
    assert policy.is_active is True


async def test_policy_lehnt_unsupported_action_ab():
    service = build_fake_data_retention_service()
    with pytest.raises(InvalidRetentionPolicyError):
        await service.create_policy(
            CreateDataRetentionPolicyRequest(
                name="Bad", entity_type="workflow_run", retention_days=90, action="delete"
            ),
            actor_user_id=uuid.uuid4(),
            actor_role="admin",
        )


async def test_policy_kann_aktualisiert_werden():
    service = build_fake_data_retention_service()
    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old Leads", entity_type="lead", retention_days=365
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    updated = await service.update_policy(
        policy.id,
        UpdateDataRetentionPolicyRequest(retention_days=180),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert updated.retention_days == 180


async def test_policy_kann_deaktiviert_werden():
    service = build_fake_data_retention_service()
    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old Leads", entity_type="lead", retention_days=365
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    deactivated = await service.deactivate_policy(
        policy.id, actor_user_id=uuid.uuid4(), actor_role="admin"
    )
    assert deactivated.is_active is False


async def test_run_gegen_unbekannte_policy_wirft_not_found():
    service = build_fake_data_retention_service()
    with pytest.raises(DataRetentionPolicyNotFoundError):
        await service.dry_run(uuid.uuid4(), actor_user_id=uuid.uuid4(), actor_role="admin")


async def test_echter_run_ohne_bestaetigung_wird_blockiert():
    service = build_fake_data_retention_service()
    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old Leads", entity_type="lead", retention_days=365
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    with pytest.raises(RetentionRunBlockedError):
        await service.run(
            policy.id,
            RunDataRetentionPolicyRequest(confirm=False),
            actor_user_id=uuid.uuid4(),
            actor_role="admin",
        )


async def test_echter_run_gegen_deaktivierte_policy_wird_blockiert():
    service = build_fake_data_retention_service()
    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old Leads", entity_type="lead", retention_days=365
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    await service.deactivate_policy(policy.id, actor_user_id=uuid.uuid4(), actor_role="admin")
    with pytest.raises(RetentionRunBlockedError):
        await service.run(
            policy.id,
            RunDataRetentionPolicyRequest(confirm=True),
            actor_user_id=uuid.uuid4(),
            actor_role="admin",
        )


# -- dry run never mutates data --------------------------------------------------


async def test_dry_run_veraendert_keine_daten():
    contacts = FakeContactRepository()
    contact = await contacts.create(
        Contact(
            company_id=uuid.uuid4(),
            first_name="Henrik",
            last_name="Hensen",
            email="henrik@example.com",
            phone="+49123456",
        )
    )
    contact.created_at = _old()
    service = build_fake_data_retention_service(contacts=contacts)
    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old Leads", entity_type="lead", retention_days=365
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    run = await service.dry_run(policy.id, actor_user_id=uuid.uuid4(), actor_role="admin")
    assert run.dry_run is True
    assert run.total_eligible == 1
    assert run.total_processed == 0

    unchanged = await contacts.get(contact.id)
    assert unchanged.email == "henrik@example.com"
    assert unchanged.first_name == "Henrik"


# -- anonymization removes sensitive fields --------------------------------------


async def test_anonymization_entfernt_sensible_contact_felder():
    contacts = FakeContactRepository()
    contact = await contacts.create(
        Contact(
            company_id=uuid.uuid4(),
            first_name="Henrik",
            last_name="Hensen",
            email="henrik@example.com",
            phone="+49123456",
        )
    )
    contact.created_at = _old()
    service = build_fake_data_retention_service(contacts=contacts)
    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old Leads", entity_type="lead", retention_days=365
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    run = await service.run(
        policy.id,
        RunDataRetentionPolicyRequest(confirm=True),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert run.total_processed == 1

    anonymized = await contacts.get(contact.id)
    assert anonymized.email is None
    assert anonymized.phone is None
    assert anonymized.first_name != "Henrik"
    assert anonymized.last_name != "Hensen"


async def test_anonymization_entfernt_sensible_reply_felder():
    replies = FakeReplyRepository()
    reply = await replies.create(
        Reply(
            provider=EmailProviderType.MOCK,
            provider_message_id="msg-1",
            from_email="prospect@example.com",
            from_name="Prospect Name",
            to_email="sales@example.com",
            subject="Re: Angebot",
            body_preview="Danke für die Info...",
            body_text="Danke für die Info, bitte kein weiteres Kontakt.",
            received_at=_old(),
        )
    )
    reply.created_at = _old()
    service = build_fake_data_retention_service(replies=replies)
    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old Replies", entity_type="reply", retention_days=180
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    run = await service.run(
        policy.id,
        RunDataRetentionPolicyRequest(confirm=True),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert run.total_processed == 1

    anonymized = await replies.get(reply.id)
    assert anonymized.from_email != "prospect@example.com"
    assert anonymized.from_name is None
    assert anonymized.to_email is None
    assert anonymized.body_preview is None
    assert anonymized.body_text is None


async def test_anonymization_ersetzt_email_draft_body():
    email_drafts = FakeEmailDraftRepository()
    draft = await email_drafts.create(
        EmailDraft(
            company_id=uuid.uuid4(),
            email_body="Sehr geehrte Damen und Herren, ...",
            subject_lines=["Ein tolles Angebot für Sie"],
        )
    )
    draft.created_at = _old()
    service = build_fake_data_retention_service(email_drafts=email_drafts)
    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old Drafts", entity_type="email_draft", retention_days=180
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    run = await service.run(
        policy.id,
        RunDataRetentionPolicyRequest(confirm=True),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert run.total_processed == 1

    anonymized = await email_drafts.get(draft.id)
    assert anonymized.email_body == "[anonymized]"
    assert anonymized.subject_lines == ["[anonymized]"]


# -- do-not-contact protection ----------------------------------------------------


async def test_aktiver_do_not_contact_eintrag_wird_nicht_geloescht():
    dnc = FakeDoNotContactRepository()
    entry = await dnc.create(
        DoNotContactEntry(reason="opt-out", email="opted-out@example.com", is_active=True)
    )
    entry.created_at = _old()
    service = build_fake_data_retention_service(do_not_contact=dnc)
    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old DNC", entity_type="do_not_contact", retention_days=1095, action="delete"
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    run = await service.run(
        policy.id,
        RunDataRetentionPolicyRequest(confirm=True),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert run.total_processed == 0
    assert run.total_eligible == 0

    still_there = await dnc.get(entry.id)
    assert still_there is not None
    assert still_there.email == "opted-out@example.com"


async def test_inaktiver_do_not_contact_eintrag_ist_eligible():
    dnc = FakeDoNotContactRepository()
    entry = await dnc.create(
        DoNotContactEntry(reason="opt-out", email="opted-out@example.com", is_active=False)
    )
    entry.created_at = _old()
    service = build_fake_data_retention_service(do_not_contact=dnc)
    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old DNC", entity_type="do_not_contact", retention_days=1095
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    run = await service.run(
        policy.id,
        RunDataRetentionPolicyRequest(confirm=True),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert run.total_processed == 1


# -- audit log is never mutated ---------------------------------------------------


async def test_audit_log_wird_nie_veraendert():
    audit_logs = FakeAuditLogRepository()
    audit = build_fake_audit_log_service(audit_logs=audit_logs)
    await audit.record(action="login", result="success")
    entry = (await audit_logs.list_filtered())[0]
    entry.created_at = _old()

    service = build_fake_data_retention_service(audit_logs=audit_logs)
    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old Audit", entity_type="audit_log", retention_days=180
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    run = await service.run(
        policy.id,
        RunDataRetentionPolicyRequest(confirm=True),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert run.total_processed == 0
    assert run.total_eligible == 1
    assert any("append-only" in w.lower() for w in run.warnings)

    unchanged = await audit_logs.list_filtered(action="login")
    assert len(unchanged) == 1
    assert unchanged[0].action == "login"


async def test_audit_events_fuer_policy_und_run_werden_erstellt():
    audit_logs = FakeAuditLogRepository()
    audit = build_fake_audit_log_service(audit_logs=audit_logs)
    service = build_fake_data_retention_service(audit=audit, audit_logs=audit_logs)

    policy = await service.create_policy(
        CreateDataRetentionPolicyRequest(
            name="Old Leads", entity_type="lead", retention_days=365
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    await service.dry_run(policy.id, actor_user_id=uuid.uuid4(), actor_role="admin")

    actions = {e.action for e in await audit_logs.list_filtered(limit=100)}
    assert "data_retention_policy_created" in actions
    assert "data_retention_dry_run_executed" in actions
    assert "data_retention_run_completed" in actions
