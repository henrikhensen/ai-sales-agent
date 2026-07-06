from abc import abstractmethod
from uuid import UUID

from backend.domain.entities.external_email_draft import ExternalEmailDraft
from backend.domain.repositories.base import AbstractRepository


class ExternalEmailDraftRepository(AbstractRepository[ExternalEmailDraft]):
    """Persistence port for :class:`ExternalEmailDraft` records.

    No business logic lives here — do-not-contact checks, review-approval
    checks, and provider selection are all the application service's job.
    """

    @abstractmethod
    async def get_by_email_draft_id(
        self, email_draft_id: UUID
    ) -> ExternalEmailDraft | None:
        """Return the external draft record for one local draft, if any."""
