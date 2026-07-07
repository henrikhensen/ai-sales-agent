"""Compliance status: a safe, at-a-glance snapshot of every guardrail.

Never returns a secret, API key, or token — only booleans/enums describing
which safeguards are active and which providers are running in mock vs.
real mode. ``email_sending_enabled`` and ``automatic_contact_enabled`` are
hard-coded ``False`` — there is no send/auto-contact capability anywhere in
this system for either to ever report otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.shared import metrics
from backend.shared.config import Settings


@dataclass(frozen=True)
class ComplianceStatus:
    do_not_contact_enabled: bool
    human_review_enabled: bool
    email_sending_enabled: bool
    automatic_contact_enabled: bool
    llm_provider: str
    llm_real_calls_enabled: bool
    email_integration_provider: str
    email_real_drafts_enabled: bool
    reply_tracking_provider: str
    reply_real_reads_enabled: bool
    rate_limits_enabled: bool
    audit_logs_enabled: bool
    last_do_not_contact_block_count: int
    last_review_block_count: int


class ComplianceStatusService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_status(self) -> ComplianceStatus:
        counters = metrics.get_counters()
        settings = self._settings
        return ComplianceStatus(
            # Both are structural, always-on safeguards in this system —
            # there is no configuration flag that could disable either.
            do_not_contact_enabled=True,
            human_review_enabled=True,
            # Hard-coded: no send/auto-contact capability exists anywhere
            # in this system for either of these to ever be True.
            email_sending_enabled=False,
            automatic_contact_enabled=False,
            llm_provider=settings.llm_provider,
            llm_real_calls_enabled=settings.llm_enable_real_calls,
            email_integration_provider=settings.email_integration_provider,
            email_real_drafts_enabled=settings.email_integration_enable_real_drafts,
            reply_tracking_provider=settings.reply_tracking_provider,
            reply_real_reads_enabled=settings.reply_tracking_enable_real_reads,
            rate_limits_enabled=settings.rate_limit_enabled,
            audit_logs_enabled=settings.audit_logs_enabled,
            last_do_not_contact_block_count=counters.do_not_contact_block_count,
            last_review_block_count=counters.review_block_count,
        )
