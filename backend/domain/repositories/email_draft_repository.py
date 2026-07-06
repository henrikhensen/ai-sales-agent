from abc import abstractmethod
from uuid import UUID

from backend.domain.entities.email_draft import EmailDraft
from backend.domain.enums import EmailDraftReviewStatus
from backend.domain.repositories.base import AbstractRepository


class EmailDraftRepository(AbstractRepository[EmailDraft]):
    """Persistence port for :class:`EmailDraft` entities."""

    @abstractmethod
    async def list_by_company(
        self, company_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[EmailDraft]:
        """Return email drafts belonging to a single company, newest first."""

    @abstractmethod
    async def update_review_status(
        self,
        email_draft_id: UUID,
        review_status: EmailDraftReviewStatus,
        reviewer_name: str | None = None,
        comment: str | None = None,
    ) -> EmailDraft | None:
        """Transition a draft's review status and record who reviewed it.

        Sets ``reviewed_at`` to the current time. Returns None if the draft
        does not exist. Never sends an email or triggers any outreach.
        """
