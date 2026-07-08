"""Tests for Customer Onboarding.

Covers: status load/create-on-first-access, step completion/skip, full
onboarding completion, and the system-wide readiness check (missing
Offer/ICP, Do-not-contact/Human Review always-on, audit logs/rate limits).
"""

import uuid

from backend.domain.entities.icp_profile import ICPProfile
from backend.domain.entities.offer_profile import OfferProfile
from backend.domain.exceptions import InvalidOnboardingStepError
from backend.shared.config import Settings
from tests.conftest import (
    FakeICPProfileRepository,
    FakeOfferProfileRepository,
    build_fake_admin_controls_service,
    build_fake_onboarding_service,
)

import pytest


async def test_onboarding_status_funktioniert():
    service = build_fake_onboarding_service()
    user_id = uuid.uuid4()
    status = await service.get_status(user_id)
    assert status.user_id == user_id
    assert status.current_step == "welcome"
    assert status.progress_percent == 0
    assert status.next_step == "welcome"


async def test_step_kann_completed_werden():
    service = build_fake_onboarding_service()
    user_id = uuid.uuid4()
    result = await service.complete_step(user_id, "welcome", actor_role="sales")
    assert "welcome" in result.status.completed_steps
    assert result.status.current_step == "profile_setup"
    assert result.status.progress_percent > 0


async def test_step_kann_skipped_werden():
    service = build_fake_onboarding_service()
    user_id = uuid.uuid4()
    result = await service.skip_step(user_id, "welcome", actor_role="sales")
    assert "welcome" in result.status.skipped_steps
    assert result.status.current_step == "profile_setup"


async def test_unbekannter_step_wirft_invalid_step_error():
    service = build_fake_onboarding_service()
    user_id = uuid.uuid4()
    with pytest.raises(InvalidOnboardingStepError):
        await service.complete_step(user_id, "not_a_real_step", actor_role="sales")


async def test_onboarding_kann_abgeschlossen_werden():
    service = build_fake_onboarding_service()
    user_id = uuid.uuid4()
    result = await service.complete_onboarding(user_id, actor_role="admin")
    assert result.status.is_completed is True
    assert result.status.completed_at is not None


async def test_completing_alle_steps_markiert_onboarding_als_completed():
    from backend.application.onboarding.schemas import ONBOARDING_STEP_ORDER

    service = build_fake_onboarding_service()
    user_id = uuid.uuid4()
    result = None
    for step in ONBOARDING_STEP_ORDER:
        result = await service.complete_step(user_id, step, actor_role="sales")
    assert result is not None
    assert result.status.is_completed is True
    assert result.status.progress_percent == 100


# -- readiness ------------------------------------------------------------------


async def test_readiness_erkennt_fehlendes_offer():
    icp_profiles = FakeICPProfileRepository()
    await icp_profiles.create(ICPProfile(name="Test ICP"))
    admin_controls = build_fake_admin_controls_service(icp_profiles=icp_profiles)
    service = build_fake_onboarding_service(
        icp_profiles=icp_profiles, admin_controls=admin_controls
    )
    readiness = await service.get_readiness()
    assert readiness.checks.has_offer_profile is False
    assert any("Offer" in b for b in readiness.blockers)
    assert readiness.readiness_level == "not_ready"


async def test_readiness_erkennt_fehlendes_icp():
    offer_profiles = FakeOfferProfileRepository()
    await offer_profiles.create(
        OfferProfile(name="Test Offer", main_value_proposition="Saves time")
    )
    admin_controls = build_fake_admin_controls_service(offer_profiles=offer_profiles)
    service = build_fake_onboarding_service(
        offer_profiles=offer_profiles, admin_controls=admin_controls
    )
    readiness = await service.get_readiness()
    assert readiness.checks.has_icp_profile is False
    assert any("ICP" in b for b in readiness.blockers)


async def test_readiness_erkennt_do_not_contact_status():
    service = build_fake_onboarding_service()
    readiness = await service.get_readiness()
    assert readiness.checks.has_do_not_contact_enabled is True


async def test_readiness_erkennt_human_review_status():
    service = build_fake_onboarding_service()
    readiness = await service.get_readiness()
    assert readiness.checks.has_human_review_enabled is True


async def test_readiness_demo_ready_mit_offer_und_icp():
    # Explicit fresh Settings(): the autouse test-safety fixture disables
    # audit_logs_enabled on the cached get_settings() singleton for the
    # whole test run, so this test needs its own instance with it back on.
    settings = Settings(AUDIT_LOGS_ENABLED=True, RATE_LIMIT_ENABLED=True)
    icp_profiles = FakeICPProfileRepository()
    offer_profiles = FakeOfferProfileRepository()
    await icp_profiles.create(ICPProfile(name="Test ICP"))
    await offer_profiles.create(
        OfferProfile(name="Test Offer", main_value_proposition="Saves time")
    )
    admin_controls = build_fake_admin_controls_service(
        icp_profiles=icp_profiles, offer_profiles=offer_profiles, settings=settings
    )
    service = build_fake_onboarding_service(
        icp_profiles=icp_profiles,
        offer_profiles=offer_profiles,
        admin_controls=admin_controls,
        settings=settings,
    )
    readiness = await service.get_readiness()
    assert readiness.checks.ready_for_demo is True
    assert readiness.readiness_level in ("demo_ready", "internal_ready", "beta_ready")


async def test_readiness_not_ready_wenn_audit_logs_deaktiviert():
    settings = Settings(AUDIT_LOGS_ENABLED=False)
    icp_profiles = FakeICPProfileRepository()
    offer_profiles = FakeOfferProfileRepository()
    await icp_profiles.create(ICPProfile(name="Test ICP"))
    await offer_profiles.create(
        OfferProfile(name="Test Offer", main_value_proposition="Saves time")
    )
    admin_controls = build_fake_admin_controls_service(
        icp_profiles=icp_profiles, offer_profiles=offer_profiles, settings=settings
    )
    service = build_fake_onboarding_service(
        icp_profiles=icp_profiles,
        offer_profiles=offer_profiles,
        admin_controls=admin_controls,
        settings=settings,
    )
    readiness = await service.get_readiness()
    assert readiness.checks.audit_logs_enabled is False
    assert readiness.readiness_level == "not_ready"


async def test_readiness_disclaimer_message_vorhanden():
    service = build_fake_onboarding_service()
    readiness = await service.get_readiness()
    assert "legally" in readiness.message.lower() or "legal" in readiness.message.lower()


async def test_readiness_safety_gate_zeigt_compliance_pack_checks():
    service = build_fake_onboarding_service()
    readiness = await service.get_readiness()
    assert readiness.checks.compliance_documents_available is True
    assert readiness.checks.data_export_available is True
    assert readiness.checks.data_subject_request_flow_available is True
    assert readiness.checks.legal_review_required_acknowledged is True
    # No policy created yet, but data retention is disabled by default —
    # "vorhanden oder bewusst disabled" is satisfied either way.
    assert readiness.checks.data_retention_config_present is True


async def test_readiness_warnt_wenn_data_retention_aktiv_ohne_policy():
    settings = Settings(DATA_RETENTION_ENABLED=True)
    service = build_fake_onboarding_service(settings=settings)
    readiness = await service.get_readiness()
    assert readiness.checks.data_retention_config_present is False
    assert any("retention" in w.lower() for w in readiness.warnings)
