"""Tests for Admin Controls.

Covers: workspace settings load/update, the get-or-create singleton
behaviour, and the safety-critical validation rules — Human Review and
Do-not-contact can never be turned off, real dispatch/manual-send are
rejected outright without the matching environment flag, and no update is
partially applied when rejected.
"""

import uuid

import pytest

from backend.application.admin.schemas import (
    UpdateAdminControlsRequest,
    UpdateWorkspaceSettingsRequest,
)
from backend.domain.exceptions import UnsafeAdminControlChangeError
from backend.shared.config import Settings
from tests.conftest import (
    FakeAuditLogRepository,
    build_fake_admin_controls_service,
    build_fake_audit_log_service,
)


async def test_workspace_settings_koennen_geladen_werden():
    service = build_fake_admin_controls_service()
    settings = await service.get_workspace_settings()
    assert settings.workspace_name
    assert settings.default_language


async def test_workspace_settings_get_or_create_ist_stabil():
    service = build_fake_admin_controls_service()
    first = await service.get_workspace_settings()
    second = await service.get_workspace_settings()
    assert first.id == second.id


async def test_workspace_settings_koennen_aktualisiert_werden():
    service = build_fake_admin_controls_service()
    updated = await service.update_workspace_settings(
        UpdateWorkspaceSettingsRequest(workspace_name="Acme Sales"),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert updated.workspace_name == "Acme Sales"


async def test_admin_controls_koennen_geladen_werden():
    service = build_fake_admin_controls_service()
    controls = await service.get_admin_controls()
    assert controls.require_human_review is True
    assert controls.require_do_not_contact_check is True
    assert controls.dispatch_mode == "draft_only"


async def test_require_human_review_kann_nicht_deaktiviert_werden():
    service = build_fake_admin_controls_service()
    with pytest.raises(UnsafeAdminControlChangeError):
        await service.update_admin_controls(
            UpdateAdminControlsRequest(require_human_review=False),
            actor_user_id=uuid.uuid4(),
            actor_role="admin",
        )
    controls = await service.get_admin_controls()
    assert controls.require_human_review is True


async def test_require_do_not_contact_check_kann_nicht_deaktiviert_werden():
    service = build_fake_admin_controls_service()
    with pytest.raises(UnsafeAdminControlChangeError):
        await service.update_admin_controls(
            UpdateAdminControlsRequest(require_do_not_contact_check=False),
            actor_user_id=uuid.uuid4(),
            actor_role="admin",
        )
    controls = await service.get_admin_controls()
    assert controls.require_do_not_contact_check is True


async def test_blockierte_aenderung_persistiert_audit_log_trotz_exception():
    """The change is rejected AND the audit trail of that rejection must
    survive — update_admin_controls uses record_independent specifically
    because it raises right after logging the block (in production, that
    raise rolls back the request's own DB session; see
    backend/infrastructure/database/session.py)."""
    audit_repo = FakeAuditLogRepository()
    audit = build_fake_audit_log_service(audit_logs=audit_repo)
    service = build_fake_admin_controls_service(audit=audit)

    with pytest.raises(UnsafeAdminControlChangeError):
        await service.update_admin_controls(
            UpdateAdminControlsRequest(require_human_review=False),
            actor_user_id=uuid.uuid4(),
            actor_role="admin",
        )

    logs = await audit_repo.list_filtered(action="unsafe_admin_control_change_blocked")
    assert len(logs) == 1
    assert logs[0].result == "blocked"
    # Nothing was saved to secrets/tokens in the reason text either.
    assert "token" not in logs[0].reason.lower()
    assert "secret" not in logs[0].reason.lower()


async def test_dispatch_mode_blockierte_aenderung_persistiert_audit_log():
    settings = Settings(OUTREACH_DISPATCH_ENABLE_REAL_SEND=False)
    audit_repo = FakeAuditLogRepository()
    audit = build_fake_audit_log_service(audit_logs=audit_repo)
    service = build_fake_admin_controls_service(settings=settings, audit=audit)

    with pytest.raises(UnsafeAdminControlChangeError):
        await service.update_admin_controls(
            UpdateAdminControlsRequest(dispatch_mode="manual_send"),
            actor_user_id=uuid.uuid4(),
            actor_role="admin",
        )

    logs = await audit_repo.list_filtered(action="unsafe_admin_control_change_blocked")
    assert len(logs) == 1
    controls = await service.get_admin_controls()
    assert controls.dispatch_mode == "draft_only"


async def test_allow_real_dispatch_wird_ohne_safety_nicht_erlaubt():
    settings = Settings(OUTREACH_DISPATCH_ENABLE_REAL_SEND=False)
    service = build_fake_admin_controls_service(settings=settings)
    with pytest.raises(UnsafeAdminControlChangeError):
        await service.update_admin_controls(
            UpdateAdminControlsRequest(allow_real_dispatch=True),
            actor_user_id=uuid.uuid4(),
            actor_role="admin",
        )
    controls = await service.get_admin_controls()
    assert controls.allow_real_dispatch is False


async def test_allow_real_dispatch_wird_mit_env_aktivierung_erlaubt():
    settings = Settings(OUTREACH_DISPATCH_ENABLE_REAL_SEND=True)
    service = build_fake_admin_controls_service(settings=settings)
    updated = await service.update_admin_controls(
        UpdateAdminControlsRequest(allow_real_dispatch=True),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert updated.allow_real_dispatch is True


async def test_dispatch_mode_manual_send_wird_ohne_env_aktivierung_nicht_erlaubt():
    settings = Settings(OUTREACH_DISPATCH_ENABLE_REAL_SEND=False)
    service = build_fake_admin_controls_service(settings=settings)
    with pytest.raises(UnsafeAdminControlChangeError):
        await service.update_admin_controls(
            UpdateAdminControlsRequest(dispatch_mode="manual_send"),
            actor_user_id=uuid.uuid4(),
            actor_role="admin",
        )
    controls = await service.get_admin_controls()
    assert controls.dispatch_mode == "draft_only"


async def test_unsichere_aenderung_wird_nicht_teilweise_angewendet():
    """A rejected update must not silently apply other fields in the same
    request — it is all-or-nothing."""
    service = build_fake_admin_controls_service()
    with pytest.raises(UnsafeAdminControlChangeError):
        await service.update_admin_controls(
            UpdateAdminControlsRequest(
                allow_real_llm_calls=True, require_human_review=False
            ),
            actor_user_id=uuid.uuid4(),
            actor_role="admin",
        )
    controls = await service.get_admin_controls()
    assert controls.allow_real_llm_calls is False


async def test_allow_real_llm_calls_gibt_warning_ohne_config():
    settings = Settings(LLM_ENABLE_REAL_CALLS=False)
    service = build_fake_admin_controls_service(settings=settings)
    updated = await service.update_admin_controls(
        UpdateAdminControlsRequest(allow_real_llm_calls=True),
        actor_user_id=uuid.uuid4(),
        actor_role="admin",
    )
    assert updated.allow_real_llm_calls is True
    assert any("allow_real_llm_calls" in w for w in updated.warnings)


async def test_setup_checklist_erkennt_fehlendes_offer_und_icp():
    service = build_fake_admin_controls_service()
    checklist = await service.get_setup_checklist()
    by_key = {item.key: item for item in checklist.items}
    assert by_key["offer_profile"].status == "blocker"
    assert by_key["icp_profile"].status == "blocker"
    assert by_key["do_not_contact"].status == "passed"
    assert by_key["human_review"].status == "passed"
    assert checklist.overall_status == "blocker"


async def test_admin_controls_zeigen_keine_secrets():
    service = build_fake_admin_controls_service()
    controls = await service.get_admin_controls()
    dumped = str(controls.model_dump()).lower()
    for forbidden in ("token", "secret", "api_key", "client_secret", "password"):
        assert forbidden not in dumped
