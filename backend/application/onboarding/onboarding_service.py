"""Customer Onboarding: tracks one user's progress through a fixed
sequence of guided setup steps, plus a system-wide readiness check.

Purely a progress tracker and a read-only readiness report — nothing here
ever enables a real provider, sends an email, contacts anyone, or creates
an external draft. Completing or skipping a step is bookkeeping only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request

from backend.application.admin.admin_controls_service import AdminControlsService
from backend.application.audit.audit_log_service import AuditLogService
from backend.application.onboarding.schemas import (
    ONBOARDING_STEP_ORDER,
    OnboardingReadinessChecks,
    OnboardingReadinessResponse,
    OnboardingStatusResponse,
    OnboardingStepUpdateResponse,
    ReadinessLevel,
)
from backend.domain.entities.onboarding_status import OnboardingStatus
from backend.domain.exceptions import InvalidOnboardingStepError
from backend.domain.repositories.data_retention_policy_repository import (
    DataRetentionPolicyRepository,
)
from backend.domain.repositories.icp_profile_repository import ICPProfileRepository
from backend.domain.repositories.offer_profile_repository import (
    OfferProfileRepository,
)
from backend.application.quality.quality_dashboard_service import (
    QualityDashboardService,
)
from backend.domain.repositories.onboarding_status_repository import (
    OnboardingStatusRepository,
)
from backend.shared.config import Settings

_READINESS_DISCLAIMER = (
    "'beta_ready' is a technical setup signal only — it does not mean real "
    "outreach use has been legally cleared. Review CUSTOMER_READINESS.md "
    "and get your own legal/compliance sign-off before contacting real "
    "prospects."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class OnboardingService:
    def __init__(
        self,
        onboarding_status: OnboardingStatusRepository,
        icp_profiles: ICPProfileRepository,
        offer_profiles: OfferProfileRepository,
        admin_controls: AdminControlsService,
        audit: AuditLogService,
        settings: Settings,
        data_retention_policies: DataRetentionPolicyRepository | None = None,
        quality_dashboard: QualityDashboardService | None = None,
    ) -> None:
        self._onboarding_status = onboarding_status
        self._icp_profiles = icp_profiles
        self._offer_profiles = offer_profiles
        self._admin_controls = admin_controls
        self._audit = audit
        self._settings = settings
        self._data_retention_policies = data_retention_policies
        self._quality_dashboard = quality_dashboard

    # -- status ---------------------------------------------------------------------

    async def _get_or_create(self, user_id: UUID) -> OnboardingStatus:
        existing = await self._onboarding_status.get_by_user_id(user_id)
        if existing is not None:
            return existing
        return await self._onboarding_status.create(OnboardingStatus(user_id=user_id))

    async def get_status(self, user_id: UUID) -> OnboardingStatusResponse:
        record = await self._get_or_create(user_id)
        return self._to_response(record)

    def _to_response(self, record: OnboardingStatus) -> OnboardingStatusResponse:
        done = set(record.completed_steps) | set(record.skipped_steps)
        progress_percent = int(
            round(100 * len(done & set(ONBOARDING_STEP_ORDER)) / len(ONBOARDING_STEP_ORDER))
        )
        next_step = next(
            (step for step in ONBOARDING_STEP_ORDER if step not in done), None
        )
        return OnboardingStatusResponse(
            id=record.id,
            user_id=record.user_id,
            current_step=record.current_step,
            completed_steps=record.completed_steps,
            skipped_steps=record.skipped_steps,
            is_completed=record.is_completed,
            completed_at=record.completed_at,
            progress_percent=min(progress_percent, 100),
            next_step=next_step,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _advance_current_step(self, record: OnboardingStatus) -> None:
        done = set(record.completed_steps) | set(record.skipped_steps)
        next_step = next(
            (step for step in ONBOARDING_STEP_ORDER if step not in done), None
        )
        if next_step is not None:
            record.current_step = next_step
        else:
            record.current_step = ONBOARDING_STEP_ORDER[-1]
            record.is_completed = True
            record.completed_at = record.completed_at or _now()

    @staticmethod
    def _validate_step(step_name: str) -> None:
        if step_name not in ONBOARDING_STEP_ORDER:
            raise InvalidOnboardingStepError(step_name)

    # -- step transitions ---------------------------------------------------------------

    async def complete_step(
        self,
        user_id: UUID,
        step_name: str,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> OnboardingStepUpdateResponse:
        self._validate_step(step_name)
        record = await self._get_or_create(user_id)
        if step_name not in record.completed_steps:
            record.completed_steps = [*record.completed_steps, step_name]
        record.skipped_steps = [s for s in record.skipped_steps if s != step_name]
        self._advance_current_step(record)
        updated = await self._onboarding_status.update(record)
        assert updated is not None

        await self._audit.record(
            action="onboarding_step_completed",
            result="success",
            actor_user_id=user_id,
            actor_role=actor_role,
            entity_type="onboarding_status",
            entity_id=updated.id,
            metadata={"step": step_name},
            request=http_request,
        )
        return OnboardingStepUpdateResponse(status=self._to_response(updated))

    async def skip_step(
        self,
        user_id: UUID,
        step_name: str,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> OnboardingStepUpdateResponse:
        self._validate_step(step_name)
        record = await self._get_or_create(user_id)
        if step_name not in record.skipped_steps:
            record.skipped_steps = [*record.skipped_steps, step_name]
        record.completed_steps = [s for s in record.completed_steps if s != step_name]
        self._advance_current_step(record)
        updated = await self._onboarding_status.update(record)
        assert updated is not None

        await self._audit.record(
            action="onboarding_step_skipped",
            result="success",
            actor_user_id=user_id,
            actor_role=actor_role,
            entity_type="onboarding_status",
            entity_id=updated.id,
            metadata={"step": step_name},
            request=http_request,
        )
        return OnboardingStepUpdateResponse(status=self._to_response(updated))

    async def complete_onboarding(
        self,
        user_id: UUID,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> OnboardingStepUpdateResponse:
        record = await self._get_or_create(user_id)
        record.is_completed = True
        record.completed_at = record.completed_at or _now()
        record.current_step = ONBOARDING_STEP_ORDER[-1]
        updated = await self._onboarding_status.update(record)
        assert updated is not None

        await self._audit.record(
            action="onboarding_completed",
            result="success",
            actor_user_id=user_id,
            actor_role=actor_role,
            entity_type="onboarding_status",
            entity_id=updated.id,
            request=http_request,
        )
        return OnboardingStepUpdateResponse(status=self._to_response(updated))

    # -- readiness ------------------------------------------------------------------

    async def get_readiness(
        self,
        actor_user_id: UUID | None = None,
        actor_role: str | None = None,
        http_request: Request | None = None,
    ) -> OnboardingReadinessResponse:
        has_offer_profile = bool(await self._offer_profiles.list(limit=1, active_only=True))
        has_icp_profile = bool(await self._icp_profiles.list(limit=1, active_only=True))
        (
            real_llm_configured,
            email_integration_configured,
            reply_tracking_configured,
            _real_send_env_enabled,
        ) = self._admin_controls.provider_config_checks()
        dispatch_safe = self._admin_controls.dispatch_safe()
        admin_status = await self._admin_controls.get_admin_controls()

        safe_mode_active = not (
            self._settings.llm_enable_real_calls
            or self._settings.email_integration_enable_real_drafts
            or self._settings.reply_tracking_enable_real_reads
        )
        audit_logs_enabled = self._settings.audit_logs_enabled
        rate_limits_enabled = self._settings.rate_limit_enabled

        blockers: list[str] = []
        if not has_offer_profile:
            blockers.append("No active Offer Profile exists yet.")
        if not has_icp_profile:
            blockers.append("No active ICP Profile exists yet.")
        if not audit_logs_enabled:
            blockers.append("Audit logs are disabled (AUDIT_LOGS_ENABLED=false).")
        if not rate_limits_enabled:
            blockers.append("Rate limits are disabled (RATE_LIMIT_ENABLED=false).")

        data_retention_config_present = True
        if self._settings.data_retention_enabled and self._data_retention_policies is not None:
            data_retention_config_present = bool(
                await self._data_retention_policies.list(limit=1)
            )

        quality_feedback_enabled = self._settings.quality_feedback_enabled
        quality_scoring_enabled = self._settings.quality_scoring_enabled
        beta_feedback_loop_available = quality_feedback_enabled and quality_scoring_enabled
        # Dispatch Readiness / Outreach Queue always respect open blocking
        # feedback where the quality repositories are wired in — a standing
        # marker of the mechanism's presence, like has_do_not_contact_enabled.
        blocking_feedback_respected = True
        quality_beta_readiness_level = "not_ready"
        if self._quality_dashboard is not None:
            quality_dashboard_data = await self._quality_dashboard.get_dashboard(
                actor_user_id=None, actor_role=None
            )
            quality_beta_readiness_level = quality_dashboard_data.beta_readiness_level

        warnings: list[str] = list(admin_status.warnings)
        if not safe_mode_active:
            warnings.append(
                "At least one provider is not running in safe/mock mode — real "
                "API calls are possible."
            )
        if not admin_status.data_export_enabled:
            warnings.append("Data export is disabled in Admin Controls.")
        if not admin_status.data_subject_requests_enabled:
            warnings.append(
                "Data subject request handling is disabled in Admin Controls."
            )
        if self._settings.data_retention_enabled and not data_retention_config_present:
            warnings.append(
                "Data retention is enabled but no retention policy has been "
                "created yet."
            )

        recommendations: list[str] = []
        if not has_offer_profile:
            recommendations.append("Create an Offer Profile under Sales Strategy → Offers.")
        if not has_icp_profile:
            recommendations.append("Create an ICP Profile under Sales Strategy → ICP.")
        if not audit_logs_enabled:
            recommendations.append("Set AUDIT_LOGS_ENABLED=true in the environment.")
        if not rate_limits_enabled:
            recommendations.append("Set RATE_LIMIT_ENABLED=true in the environment.")
        if warnings:
            recommendations.append("Review Admin Controls before enabling any real provider.")
        recommendations.append(
            "Read CUSTOMER_READINESS.md before any real customer-facing use."
        )
        recommendations.append(
            "Review Compliance Documents (GET /api/v1/compliance/documents) "
            "and COMPLIANCE.md before any real customer-facing use."
        )

        ready_for_demo = (
            has_offer_profile
            and has_icp_profile
            and audit_logs_enabled
            and rate_limits_enabled
        )
        ready_for_internal_use = ready_for_demo and dispatch_safe and safe_mode_active
        ready_for_customer_beta = ready_for_internal_use and not warnings

        if not ready_for_demo:
            readiness_level: ReadinessLevel = "not_ready"
        elif not ready_for_internal_use:
            readiness_level = "demo_ready"
        elif not ready_for_customer_beta:
            readiness_level = "internal_ready"
        else:
            readiness_level = "beta_ready"

        checks = OnboardingReadinessChecks(
            has_offer_profile=has_offer_profile,
            has_icp_profile=has_icp_profile,
            has_do_not_contact_enabled=True,
            has_human_review_enabled=True,
            safe_mode_active=safe_mode_active,
            real_llm_configured=real_llm_configured,
            email_integration_configured=email_integration_configured,
            reply_tracking_configured=reply_tracking_configured,
            dispatch_safe=dispatch_safe,
            audit_logs_enabled=audit_logs_enabled,
            rate_limits_enabled=rate_limits_enabled,
            compliance_documents_available=True,
            data_retention_config_present=data_retention_config_present,
            data_export_available=admin_status.data_export_enabled,
            data_subject_request_flow_available=admin_status.data_subject_requests_enabled,
            legal_review_required_acknowledged=True,
            ready_for_demo=ready_for_demo,
            ready_for_internal_use=ready_for_internal_use,
            ready_for_customer_beta=ready_for_customer_beta,
            quality_feedback_enabled=quality_feedback_enabled,
            quality_scoring_enabled=quality_scoring_enabled,
            beta_feedback_loop_available=beta_feedback_loop_available,
            blocking_feedback_respected=blocking_feedback_respected,
            quality_beta_readiness_level=quality_beta_readiness_level,
        )

        await self._audit.record(
            action="onboarding_readiness_checked",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="onboarding_readiness",
            metadata={"readiness_level": readiness_level},
            request=http_request,
        )

        return OnboardingReadinessResponse(
            readiness_level=readiness_level,
            blockers=blockers,
            warnings=warnings,
            recommendations=recommendations,
            checks=checks,
            message=_READINESS_DISCLAIMER,
        )
