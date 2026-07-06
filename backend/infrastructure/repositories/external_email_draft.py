from uuid import UUID

from sqlalchemy import select

from backend.domain.entities.external_email_draft import ExternalEmailDraft
from backend.domain.repositories.external_email_draft_repository import (
    ExternalEmailDraftRepository,
)
from backend.infrastructure.database.models.external_email_draft import (
    ExternalEmailDraftModel,
)
from backend.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyExternalEmailDraftRepository(
    SQLAlchemyRepository[ExternalEmailDraftModel, ExternalEmailDraft],
    ExternalEmailDraftRepository,
):
    """SQLAlchemy-backed :class:`ExternalEmailDraftRepository`."""

    model = ExternalEmailDraftModel

    def _to_entity(self, orm_obj: ExternalEmailDraftModel) -> ExternalEmailDraft:
        return ExternalEmailDraft(
            id=orm_obj.id,
            email_draft_id=orm_obj.email_draft_id,
            provider=orm_obj.provider,
            provider_status=orm_obj.provider_status,
            provider_draft_id=orm_obj.provider_draft_id,
            provider_draft_url=orm_obj.provider_draft_url,
            created_by_user_id=orm_obj.created_by_user_id,
            last_error=orm_obj.last_error,
            is_active=orm_obj.is_active,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _to_orm(self, entity: ExternalEmailDraft) -> ExternalEmailDraftModel:
        return ExternalEmailDraftModel(
            email_draft_id=entity.email_draft_id,
            provider=entity.provider,
            provider_status=entity.provider_status,
            provider_draft_id=entity.provider_draft_id,
            provider_draft_url=entity.provider_draft_url,
            created_by_user_id=entity.created_by_user_id,
            last_error=entity.last_error,
            is_active=entity.is_active,
        )

    def _apply(
        self, orm_obj: ExternalEmailDraftModel, entity: ExternalEmailDraft
    ) -> None:
        orm_obj.provider = entity.provider
        orm_obj.provider_status = entity.provider_status
        orm_obj.provider_draft_id = entity.provider_draft_id
        orm_obj.provider_draft_url = entity.provider_draft_url
        orm_obj.last_error = entity.last_error
        orm_obj.is_active = entity.is_active

    async def get_by_email_draft_id(
        self, email_draft_id: UUID
    ) -> ExternalEmailDraft | None:
        stmt = select(ExternalEmailDraftModel).where(
            ExternalEmailDraftModel.email_draft_id == email_draft_id
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None
