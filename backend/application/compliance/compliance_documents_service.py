"""Compliance Documents: static, informational templates and notices.

Every document here is a template or a notice, never legal advice and
never a certification. Nothing in this system has been reviewed by a
lawyer on the operator's behalf, and nothing here claims compliance with
any specific law or standard (GDPR, CCPA, or otherwise). See
COMPLIANCE.md and CUSTOMER_READINESS.md for the full picture, and get
your own legal/compliance review before any real customer-facing use.
"""

from __future__ import annotations

from backend.application.compliance.compliance_documents_schemas import (
    ComplianceDocument,
    ComplianceDocumentsResponse,
)
from backend.shared.config import Settings

_DISCLAIMER = (
    "These documents are templates and informational notices only — not "
    "legal advice, and not a certification of compliance with any law or "
    "standard. Real customer-facing use requires your own legal/compliance "
    "review. See COMPLIANCE.md and CUSTOMER_READINESS.md."
)


class ComplianceDocumentsService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_documents(self) -> ComplianceDocumentsResponse:
        return ComplianceDocumentsResponse(
            documents=[
                self._privacy_notice_template(),
                self._data_processing_summary(),
                self._subprocessors_summary(),
                self._data_retention_summary(),
                self._user_responsibility_notice(),
                self._outreach_safety_notice(),
                self._provider_data_transfer_notice(),
                self._legal_review_required_notice(),
            ],
            disclaimer=_DISCLAIMER,
        )

    def _privacy_notice_template(self) -> ComplianceDocument:
        return ComplianceDocument(
            key="privacy_notice_template",
            title="Privacy Notice Template",
            body=(
                "A starting point for your own privacy notice — not a "
                "ready-to-publish document. This system processes business "
                "contact data (company names, work emails, phone numbers "
                "where provided) to support sales outreach preparation. "
                "Replace every bracketed placeholder with your own details "
                "(company name, contact address, legal basis, data subject "
                "rights process) and have it reviewed by qualified legal "
                "counsel before publishing it to real customers or contacts."
            ),
        )

    def _data_processing_summary(self) -> ComplianceDocument:
        return ComplianceDocument(
            key="data_processing_summary",
            title="Data Processing Summary",
            body=(
                "Data processed: company/lead/contact records, email "
                "drafts (never sent automatically), inbound replies (read "
                "and stored, never auto-answered), workflow run history, "
                "and do-not-contact entries. No LinkedIn or logged-in-page "
                "scraping is performed, and no personal email address is "
                "ever guessed. Real LLM/email/reply-tracking provider "
                "calls only happen when explicitly enabled via environment "
                "configuration (Mock is the default everywhere)."
            ),
        )

    def _subprocessors_summary(self) -> ComplianceDocument:
        return ComplianceDocument(
            key="subprocessors_summary",
            title="Subprocessors Summary",
            body=(
                "In Mock mode (the default), no third-party subprocessor is "
                "ever called. If you explicitly enable a real provider "
                "(e.g. an LLM API, Gmail/Outlook, or a reply-tracking "
                "provider), that provider becomes a subprocessor for the "
                "data it touches — check its own data processing terms and "
                "list it in your own subprocessors disclosure before "
                "enabling it for real customer data."
            ),
        )

    def _data_retention_summary(self) -> ComplianceDocument:
        return ComplianceDocument(
            key="data_retention_summary",
            title="Data Retention Summary",
            body=(
                "Data Retention Policies are disabled by default "
                f"(DATA_RETENTION_ENABLED={self._settings.data_retention_enabled}). "
                "When enabled, every real (non-dry-run) run anonymizes "
                "rather than deletes unless a policy explicitly overrides "
                "that, and requires explicit admin confirmation. A dry run "
                "never changes data. Do-not-contact entries that are still "
                "active are never touched by any retention run, regardless "
                "of age. Audit logs are append-only and are never deleted "
                "or anonymized by any run."
            ),
        )

    def _user_responsibility_notice(self) -> ComplianceDocument:
        return ComplianceDocument(
            key="user_responsibility_notice",
            title="User Responsibility Notice",
            body=(
                "You (the operator) remain responsible for having a lawful "
                "basis to process and contact the people and companies you "
                "add to this system, for honoring opt-out/do-not-contact "
                "requests, and for reviewing every email draft before any "
                "external action. This system enforces do-not-contact and "
                "human review as non-negotiable technical gates, but it "
                "cannot verify your legal basis for contact — that "
                "judgment call is yours."
            ),
        )

    def _outreach_safety_notice(self) -> ComplianceDocument:
        return ComplianceDocument(
            key="outreach_safety_notice",
            title="Outreach Safety Notice",
            body=(
                "No email is ever sent automatically by this system. There "
                "is no batch-send, mass-send, or reply-send capability "
                "anywhere in the API. 'Approved' means only that a human "
                "has internally reviewed a draft — never that it has been "
                "sent. Creating an external draft (Gmail/Outlook) always "
                "requires an explicit, manual action, and real message "
                "sending is only ever simulated by the Mock provider — no "
                "send scope is ever requested from a real email provider."
            ),
        )

    def _provider_data_transfer_notice(self) -> ComplianceDocument:
        return ComplianceDocument(
            key="provider_data_transfer_notice",
            title="Provider Data Transfer Notice",
            body=(
                "If you enable a real LLM, email integration, or reply-"
                "tracking provider, data you process (lead/company/email "
                "content) will be transferred to that provider's "
                "infrastructure, which may be outside your jurisdiction. "
                "Review each provider's own data processing and "
                "international-transfer terms before enabling it for real "
                "customer or prospect data."
            ),
        )

    def _legal_review_required_notice(self) -> ComplianceDocument:
        return ComplianceDocument(
            key="legal_review_required_notice",
            title="Legal Review Required Notice",
            body=(
                "None of the documents in this Compliance Pack constitute "
                "legal advice, and nothing in this system is certified "
                "compliant with GDPR, CCPA, CAN-SPAM, or any other law or "
                "standard. This pack is prepared for a legal/compliance "
                "review, not a substitute for one. Get your own qualified "
                "legal review before contacting real prospects or "
                "onboarding a real paying customer — see "
                "CUSTOMER_READINESS.md."
            ),
        )
