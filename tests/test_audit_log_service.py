"""Unit tests for backend/application/audit/audit_log_service.py.

No database involved — uses FakeAuditLogRepository.
"""

import uuid

import pytest

from backend.application.audit.audit_log_service import hash_ip
from backend.domain.exceptions import AuditLogNotFoundError
from tests.conftest import FakeAuditLogRepository, build_fake_audit_log_service


async def test_record_creates_an_entry_when_enabled():
    repo = FakeAuditLogRepository()
    service = build_fake_audit_log_service(audit_logs=repo)

    await service.record(action="login", result="success", actor_user_id=uuid.uuid4())

    entries = await repo.list_filtered()
    assert len(entries) == 1
    assert entries[0].action == "login"
    assert entries[0].result == "success"


async def test_record_is_a_no_op_when_audit_logs_disabled():
    from backend.shared.config import Settings

    repo = FakeAuditLogRepository()
    service = build_fake_audit_log_service(
        audit_logs=repo, settings=Settings(AUDIT_LOGS_ENABLED=False)
    )

    await service.record(action="login", result="success")

    entries = await repo.list_filtered()
    assert entries == []


async def test_record_strips_sensitive_metadata_keys():
    repo = FakeAuditLogRepository()
    service = build_fake_audit_log_service(audit_logs=repo)

    await service.record(
        action="llm_test_executed",
        result="success",
        metadata={
            "provider": "mock",
            "api_key": "sk-should-not-be-stored",
            "password": "should-not-be-stored",
            "prompt": "full prompt text should not be stored",
        },
    )

    entries = await repo.list_filtered()
    assert entries[0].metadata == {"provider": "mock"}


async def test_record_truncates_long_metadata_values():
    repo = FakeAuditLogRepository()
    service = build_fake_audit_log_service(audit_logs=repo)

    long_value = "x" * 1000
    await service.record(
        action="reply_sync_completed", result="success", metadata={"note": long_value}
    )

    entries = await repo.list_filtered()
    assert len(entries[0].metadata["note"]) < len(long_value)


async def test_record_never_raises_when_repository_fails():
    class _BrokenRepository(FakeAuditLogRepository):
        async def create(self, entry):
            raise RuntimeError("simulated DB failure")

    service = build_fake_audit_log_service(audit_logs=_BrokenRepository())

    # Must not raise — a logging failure must never break the caller.
    await service.record(action="login", result="success")


async def test_get_raises_not_found_for_unknown_id():
    service = build_fake_audit_log_service()
    with pytest.raises(AuditLogNotFoundError):
        await service.get(uuid.uuid4())


async def test_list_filtered_by_action_and_result():
    repo = FakeAuditLogRepository()
    service = build_fake_audit_log_service(audit_logs=repo)

    await service.record(action="login", result="success")
    await service.record(action="login", result="failed")
    await service.record(action="sales_workflow_started", result="started")

    response = await service.list_filtered(action="login")
    assert len(response.items) == 2
    assert all(item.action == "login" for item in response.items)

    response = await service.list_filtered(action="login", result="failed")
    assert len(response.items) == 1
    assert response.items[0].result == "failed"


def test_hash_ip_never_returns_the_raw_ip():
    hashed = hash_ip("203.0.113.42")
    assert "203.0.113.42" not in hashed
    assert len(hashed) > 0
