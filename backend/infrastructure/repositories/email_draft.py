from uuid import UUID

from sqlalchemy import select

from backend.domain.entities.email_draft import EmailDraft
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.infrastructure.database.models.email_draft import EmailDraftModel
from backend.infrastructure.repositories.base import SQLAlchemyRepository


class SQLAlchemyEmailDraftRepository(
    SQLAlchemyRepository[EmailDraftModel, EmailDraft], EmailDraftRepository
):
    """SQLAlchemy-backed :class:`EmailDraftRepository`."""

    model = EmailDraftModel

    def _to_entity(self, orm_obj: EmailDraftModel) -> EmailDraft:
        return EmailDraft(
            id=orm_obj.id,
            company_id=orm_obj.company_id,
            lead_id=orm_obj.lead_id,
            workflow_run_id=orm_obj.workflow_run_id,
            subject_lines=orm_obj.subject_lines,
            email_body=orm_obj.email_body,
            status=orm_obj.status,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )

    def _to_orm(self, entity: EmailDraft) -> EmailDraftModel:
        return EmailDraftModel(
            company_id=entity.company_id,
            lead_id=entity.lead_id,
            workflow_run_id=entity.workflow_run_id,
            subject_lines=entity.subject_lines,
            email_body=entity.email_body,
            status=entity.status,
        )

    def _apply(self, orm_obj: EmailDraftModel, entity: EmailDraft) -> None:
        orm_obj.lead_id = entity.lead_id
        orm_obj.workflow_run_id = entity.workflow_run_id
        orm_obj.subject_lines = entity.subject_lines
        orm_obj.email_body = entity.email_body
        orm_obj.status = entity.status

    async def list_by_company(
        self, company_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[EmailDraft]:
        stmt = (
            select(EmailDraftModel)
            .where(EmailDraftModel.company_id == company_id)
            .order_by(EmailDraftModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]
