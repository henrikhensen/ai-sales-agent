from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.workflow_run import WorkflowRun
from backend.domain.enums import WorkflowReviewStatus
from backend.domain.repositories.workflow_run_repository import WorkflowRunRepository
from backend.infrastructure.database.models.workflow_run import WorkflowRunModel


class SQLAlchemyWorkflowRunRepository(WorkflowRunRepository):
    """SQLAlchemy-backed :class:`WorkflowRunRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: WorkflowRun) -> WorkflowRun:
        orm_obj = WorkflowRunModel(
            company_name=run.company_name,
            workflow_type=run.workflow_type,
            status=run.status,
            review_status=run.review_status,
            input_payload=run.input_payload,
            result_payload=run.result_payload,
            confidence_score=run.confidence_score,
            missing_information=run.missing_information,
            compliance_notes=run.compliance_notes,
            company_id=run.company_id,
            lead_id=run.lead_id,
            contact_id=run.contact_id,
            email_draft_id=run.email_draft_id,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, run_id: UUID) -> WorkflowRun | None:
        orm_obj = await self._session.get(WorkflowRunModel, run_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        company_name: str | None = None,
        review_status: WorkflowReviewStatus | None = None,
    ) -> list[WorkflowRun]:
        stmt = select(WorkflowRunModel).order_by(WorkflowRunModel.created_at.desc())
        if company_name:
            stmt = stmt.where(WorkflowRunModel.company_name.ilike(f"%{company_name}%"))
        if review_status is not None:
            stmt = stmt.where(WorkflowRunModel.review_status == review_status)
        stmt = stmt.limit(limit).offset(offset)

        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    async def update_review_status(
        self, run_id: UUID, review_status: WorkflowReviewStatus
    ) -> WorkflowRun | None:
        orm_obj = await self._session.get(WorkflowRunModel, run_id)
        if orm_obj is None:
            return None
        orm_obj.review_status = review_status
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def update_crm_links(
        self,
        run_id: UUID,
        company_id: UUID | None = None,
        lead_id: UUID | None = None,
        contact_id: UUID | None = None,
        email_draft_id: UUID | None = None,
    ) -> WorkflowRun | None:
        orm_obj = await self._session.get(WorkflowRunModel, run_id)
        if orm_obj is None:
            return None
        if company_id is not None:
            orm_obj.company_id = company_id
        if lead_id is not None:
            orm_obj.lead_id = lead_id
        if contact_id is not None:
            orm_obj.contact_id = contact_id
        if email_draft_id is not None:
            orm_obj.email_draft_id = email_draft_id
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    @staticmethod
    def _to_entity(orm_obj: WorkflowRunModel) -> WorkflowRun:
        return WorkflowRun(
            id=orm_obj.id,
            company_name=orm_obj.company_name,
            workflow_type=orm_obj.workflow_type,
            status=orm_obj.status,
            review_status=orm_obj.review_status,
            input_payload=orm_obj.input_payload,
            result_payload=orm_obj.result_payload,
            confidence_score=orm_obj.confidence_score,
            missing_information=orm_obj.missing_information,
            compliance_notes=orm_obj.compliance_notes,
            company_id=orm_obj.company_id,
            lead_id=orm_obj.lead_id,
            contact_id=orm_obj.contact_id,
            email_draft_id=orm_obj.email_draft_id,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
        )
