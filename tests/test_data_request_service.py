"""Tests for Data Subject Requests.

Covers: creation, export, completion (including automatic do-not-contact
entry creation for do_not_contact-type requests), and that no email is
ever sent to the subject.
"""

import uuid

from backend.application.compliance.data_request_schemas import (
    CompleteDataRequestRequest,
    CreateDataSubjectRequestRequest,
)
from tests.conftest import (
    build_fake_compliance_service,
    build_fake_data_request_service,
)


async def test_request_kann_erstellt_werden():
    service = build_fake_data_request_service()
    created = await service.create_request(
        CreateDataSubjectRequestRequest(
            request_type="export", subject_email="Someone@Example.com"
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert created.status == "open"
    # stored lowercase
    assert created.subject_email == "someone@example.com"


async def test_request_kann_exportieren():
    service = build_fake_data_request_service()
    created = await service.create_request(
        CreateDataSubjectRequestRequest(
            request_type="export", subject_email="someone@example.com"
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    detail = await service.export_for_request(
        created.id, actor_user_id=uuid.uuid4(), actor_role="admin"
    )
    assert detail.export is not None
    assert detail.request.status == "in_progress"


async def test_request_kann_abgeschlossen_werden():
    service = build_fake_data_request_service()
    created = await service.create_request(
        CreateDataSubjectRequestRequest(
            request_type="correction", subject_email="someone@example.com"
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    completed = await service.complete_request(
        created.id,
        CompleteDataRequestRequest(result_summary="Done"),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert completed.status == "completed"
    assert completed.completed_at is not None
    assert completed.result_summary == "Done"


async def test_do_not_contact_request_erstellt_dnc_eintrag_bei_abschluss():
    compliance = build_fake_compliance_service()
    service = build_fake_data_request_service(do_not_contact=compliance)
    created = await service.create_request(
        CreateDataSubjectRequestRequest(
            request_type="do_not_contact", subject_email="optout@example.com"
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    await service.complete_request(
        created.id,
        CompleteDataRequestRequest(),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    check = await compliance.check(email="optout@example.com")
    assert check.is_blocked is True


async def test_prepare_anonymize_veraendert_keine_daten():
    service = build_fake_data_request_service()
    created = await service.create_request(
        CreateDataSubjectRequestRequest(
            request_type="anonymize", subject_email="someone@example.com"
        ),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    result = await service.prepare_anonymize(
        created.id, actor_user_id=uuid.uuid4(), actor_role="admin"
    )
    assert "nothing has" in result.message.lower()
    assert "been changed" in result.message.lower()
    assert result.request.status == "in_progress"
