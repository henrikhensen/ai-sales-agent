from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.workspace_settings import WorkspaceSettings
from backend.domain.repositories.workspace_settings_repository import (
    WorkspaceSettingsRepository,
)
from backend.infrastructure.database.models.workspace_settings import (
    WorkspaceSettingsModel,
)


class SQLAlchemyWorkspaceSettingsRepository(WorkspaceSettingsRepository):
    """SQLAlchemy-backed :class:`WorkspaceSettingsRepository`.

    Single-tenant: always returns/updates the first (and only expected)
    row.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self) -> WorkspaceSettings | None:
        stmt = select(WorkspaceSettingsModel).limit(1)
        result = await self._session.execute(stmt)
        orm_obj = result.scalars().first()
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def create(self, settings: WorkspaceSettings) -> WorkspaceSettings:
        orm_obj = WorkspaceSettingsModel(
            workspace_name=settings.workspace_name,
            company_name=settings.company_name,
            company_website=settings.company_website,
            default_language=settings.default_language,
            default_tone=settings.default_tone,
            default_icp_profile_id=settings.default_icp_profile_id,
            default_offer_profile_id=settings.default_offer_profile_id,
            require_human_review=settings.require_human_review,
            require_do_not_contact_check=settings.require_do_not_contact_check,
            allow_real_llm_calls=settings.allow_real_llm_calls,
            allow_real_email_drafts=settings.allow_real_email_drafts,
            allow_real_reply_reads=settings.allow_real_reply_reads,
            allow_real_dispatch=settings.allow_real_dispatch,
            dispatch_mode=settings.dispatch_mode,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def update(self, settings: WorkspaceSettings) -> WorkspaceSettings | None:
        orm_obj = await self._session.get(WorkspaceSettingsModel, settings.id)
        if orm_obj is None:
            return None
        orm_obj.workspace_name = settings.workspace_name
        orm_obj.company_name = settings.company_name
        orm_obj.company_website = settings.company_website
        orm_obj.default_language = settings.default_language
        orm_obj.default_tone = settings.default_tone
        orm_obj.default_icp_profile_id = settings.default_icp_profile_id
        orm_obj.default_offer_profile_id = settings.default_offer_profile_id
        orm_obj.require_human_review = settings.require_human_review
        orm_obj.require_do_not_contact_check = settings.require_do_not_contact_check
        orm_obj.allow_real_llm_calls = settings.allow_real_llm_calls
        orm_obj.allow_real_email_drafts = settings.allow_real_email_drafts
        orm_obj.allow_real_reply_reads = settings.allow_real_reply_reads
        orm_obj.allow_real_dispatch = settings.allow_real_dispatch
        orm_obj.dispatch_mode = settings.dispatch_mode
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    @staticmethod
    def _to_entity(orm_obj: WorkspaceSettingsModel) -> WorkspaceSettings:
        return WorkspaceSettings(
            id=orm_obj.id,
            workspace_name=orm_obj.workspace_name,
            company_name=orm_obj.company_name,
            company_website=orm_obj.company_website,
            default_language=orm_obj.default_language,
            default_tone=orm_obj.default_tone,
            default_icp_profile_id=orm_obj.default_icp_profile_id,
            default_offer_profile_id=orm_obj.default_offer_profile_id,
            require_human_review=orm_obj.require_human_review,
            require_do_not_contact_check=orm_obj.require_do_not_contact_check,
            allow_real_llm_calls=orm_obj.allow_real_llm_calls,
            allow_real_email_drafts=orm_obj.allow_real_email_drafts,
            allow_real_reply_reads=orm_obj.allow_real_reply_reads,
            allow_real_dispatch=orm_obj.allow_real_dispatch,
            dispatch_mode=orm_obj.dispatch_mode,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
