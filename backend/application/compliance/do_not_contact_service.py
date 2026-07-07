"""Do-not-contact (opt-out) compliance service.

Opt-out takes precedence over the Sales Workflow and Human Review: see
``backend.application.workflows.sales_workflow.SalesWorkflowService`` (skips
Email Draft creation on a match, response carries the compliance warning)
and ``backend.application.reviews.review_service.ReviewService`` (refuses to
approve a blocked email draft). This service itself never sends an email,
contacts anyone, or makes any external call — it only ever creates, lists,
updates, and checks opt-out records.
"""

from __future__ import annotations

from uuid import UUID

from backend.application.compliance.schemas import (
    CreateDoNotContactRequest,
    DoNotContactCheckResponse,
    DoNotContactEntryResponse,
    DoNotContactListResponse,
    UpdateDoNotContactRequest,
)
from backend.domain.entities.do_not_contact_entry import DoNotContactEntry
from backend.domain.exceptions import DoNotContactEntryNotFoundError
from backend.domain.repositories.do_not_contact_repository import (
    DoNotContactRepository,
)
from backend.shared.metrics import increment_do_not_contact_block_count

def normalize_company_name(value: str) -> str:
    """Lowercase and collapse whitespace, for matching only (not display)."""
    return " ".join(value.strip().lower().split())


class DoNotContactService:
    """Creates, lists, updates, and checks do-not-contact entries."""

    def __init__(self, entries: DoNotContactRepository) -> None:
        self._entries = entries

    async def create_entry(
        self,
        request: CreateDoNotContactRequest,
        created_by_user_id: UUID | None,
    ) -> DoNotContactEntryResponse:
        email = request.email.strip().lower() if request.email else None
        domain = request.domain.strip().lower() if request.domain else None
        company_name = request.company_name.strip() if request.company_name else None

        entry = DoNotContactEntry(
            reason=request.reason,
            email=email,
            domain=domain,
            company_name=company_name,
            company_name_normalized=(
                normalize_company_name(company_name) if company_name else None
            ),
            source=request.source,
            is_active=True,
            created_by_user_id=created_by_user_id,
        )
        created = await self._entries.create(entry)
        return DoNotContactEntryResponse.model_validate(created)

    async def list_entries(
        self, limit: int = 100, offset: int = 0
    ) -> DoNotContactListResponse:
        entries = await self._entries.list(limit=limit, offset=offset)
        return DoNotContactListResponse(
            items=[DoNotContactEntryResponse.model_validate(e) for e in entries],
            limit=limit,
            offset=offset,
        )

    async def update_entry(
        self, entry_id: UUID, request: UpdateDoNotContactRequest
    ) -> DoNotContactEntryResponse:
        existing = await self._entries.get(entry_id)
        if existing is None:
            raise DoNotContactEntryNotFoundError(entry_id)

        updates = request.model_dump(exclude_unset=True)
        if "email" in updates:
            existing.email = updates["email"].strip().lower() if updates["email"] else None
        if "domain" in updates:
            existing.domain = (
                updates["domain"].strip().lower() if updates["domain"] else None
            )
        if "company_name" in updates:
            company_name = updates["company_name"]
            existing.company_name = company_name.strip() if company_name else None
            existing.company_name_normalized = (
                normalize_company_name(company_name) if company_name else None
            )
        if "reason" in updates:
            existing.reason = updates["reason"]
        if "is_active" in updates:
            existing.is_active = updates["is_active"]

        updated = await self._entries.update(existing)
        if updated is None:
            raise DoNotContactEntryNotFoundError(entry_id)
        return DoNotContactEntryResponse.model_validate(updated)

    async def deactivate_entry(self, entry_id: UUID) -> DoNotContactEntryResponse:
        updated = await self._entries.deactivate(entry_id)
        if updated is None:
            raise DoNotContactEntryNotFoundError(entry_id)
        return DoNotContactEntryResponse.model_validate(updated)

    async def check(
        self,
        *,
        email: str | None = None,
        domain: str | None = None,
        company_name: str | None = None,
    ) -> DoNotContactCheckResponse:
        """Check email/domain/company_name against active opt-out entries.

        Matching rules: an exact (case-insensitive) email match blocks; a
        domain match blocks every email at that domain (an email's own
        domain is checked too, even if no separate ``domain`` was passed); a
        company_name match blocks that company. Inactive entries never
        block. Checked in order email -> domain -> company_name; the first
        match wins.
        """
        normalized_email = email.strip().lower() if email else None
        normalized_domain = domain.strip().lower() if domain else None

        if normalized_email:
            match = await self._entries.find_active_by_email(normalized_email)
            if match is not None:
                return self._blocked(match, "email")

        email_domain = (
            normalized_email.rsplit("@", 1)[1]
            if normalized_email and "@" in normalized_email
            else None
        )
        for candidate_domain in dict.fromkeys(
            filter(None, [normalized_domain, email_domain])
        ):
            match = await self._entries.find_active_by_domain(candidate_domain)
            if match is not None:
                return self._blocked(match, "domain")

        if company_name:
            match = await self._entries.find_active_by_company_name(
                normalize_company_name(company_name)
            )
            if match is not None:
                return self._blocked(match, "company_name")

        return DoNotContactCheckResponse(is_blocked=False)

    @staticmethod
    def _blocked(
        entry: DoNotContactEntry, matched_by: str
    ) -> DoNotContactCheckResponse:
        increment_do_not_contact_block_count()
        return DoNotContactCheckResponse(
            is_blocked=True,
            matched_by=matched_by,
            matched_entry_id=entry.id,
            reason=entry.reason,
            warning_message=(
                "Do-not-contact blockiert Outreach: "
                f"{matched_by} entspricht einem aktiven Opt-out-Eintrag."
            ),
        )
