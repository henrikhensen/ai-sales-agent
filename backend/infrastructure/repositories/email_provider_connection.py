from uuid import UUID

from sqlalchemy import select

from backend.domain.entities.email_provider_connection import EmailProviderConnection
from backend.domain.enums import EmailProviderType
from backend.domain.repositories.email_provider_connection_repository import (
    EmailProviderConnectionRepository,
)
from backend.infrastructure.database.models.email_provider_connection import (
    EmailProviderConnectionModel,
)
from backend.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyEmailProviderConnectionRepository(
    SQLAlchemyRepository[EmailProviderConnectionModel, EmailProviderConnection],
    EmailProviderConnectionRepository,
):
    """SQLAlchemy-backed :class:`EmailProviderConnectionRepository`."""

    model = EmailProviderConnectionModel

    def _to_entity(
        self, orm_obj: EmailProviderConnectionModel
    ) -> EmailProviderConnection:
        return EmailProviderConnection(
            id=orm_obj.id,
            user_id=orm_obj.user_id,
            provider=orm_obj.provider,
            encrypted_access_token=orm_obj.encrypted_access_token,
            encrypted_refresh_token=orm_obj.encrypted_refresh_token,
            token_expires_at=orm_obj.token_expires_at,
            scope=orm_obj.scope,
            external_account_email=orm_obj.external_account_email,
            is_active=orm_obj.is_active,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _to_orm(
        self, entity: EmailProviderConnection
    ) -> EmailProviderConnectionModel:
        return EmailProviderConnectionModel(
            user_id=entity.user_id,
            provider=entity.provider,
            encrypted_access_token=entity.encrypted_access_token,
            encrypted_refresh_token=entity.encrypted_refresh_token,
            token_expires_at=entity.token_expires_at,
            scope=entity.scope,
            external_account_email=entity.external_account_email,
            is_active=entity.is_active,
        )

    def _apply(
        self, orm_obj: EmailProviderConnectionModel, entity: EmailProviderConnection
    ) -> None:
        orm_obj.encrypted_access_token = entity.encrypted_access_token
        orm_obj.encrypted_refresh_token = entity.encrypted_refresh_token
        orm_obj.token_expires_at = entity.token_expires_at
        orm_obj.scope = entity.scope
        orm_obj.external_account_email = entity.external_account_email
        orm_obj.is_active = entity.is_active

    async def get_active_for_user(
        self, user_id: UUID, provider: EmailProviderType
    ) -> EmailProviderConnection | None:
        stmt = select(EmailProviderConnectionModel).where(
            EmailProviderConnectionModel.user_id == user_id,
            EmailProviderConnectionModel.provider == provider,
            EmailProviderConnectionModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def deactivate_for_user(
        self, user_id: UUID, provider: EmailProviderType
    ) -> EmailProviderConnection | None:
        stmt = select(EmailProviderConnectionModel).where(
            EmailProviderConnectionModel.user_id == user_id,
            EmailProviderConnectionModel.provider == provider,
            EmailProviderConnectionModel.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        if orm_obj is None:
            return None
        orm_obj.is_active = False
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)
