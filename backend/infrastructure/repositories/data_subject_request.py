from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.entities.data_subject_request import DataSubjectRequest
from backend.domain.repositories.data_subject_request_repository import (
    DataSubjectRequestRepository,
)
from backend.infrastructure.database.models.data_subject_request import (
    DataSubjectRequestModel,
)


class SQLAlchemyDataSubjectRequestRepository(DataSubjectRequestRepository):
    """SQLAlchemy-backed :class:`DataSubjectRequestRepository`."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, request: DataSubjectRequest) -> DataSubjectRequest:
        orm_obj = DataSubjectRequestModel(
            request_type=request.request_type,
            subject_email=request.subject_email,
            subject_domain=request.subject_domain,
            subject_name=request.subject_name,
            status=request.status,
            requested_by_user_id=request.requested_by_user_id,
            handled_by_user_id=request.handled_by_user_id,
            notes=request.notes,
            result_summary=request.result_summary,
            completed_at=request.completed_at,
        )
        self._session.add(orm_obj)
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def get_by_id(self, request_id: UUID) -> DataSubjectRequest | None:
        orm_obj = await self._session.get(DataSubjectRequestModel, request_id)
        return self._to_entity(orm_obj) if orm_obj is not None else None

    async def update(
        self, request: DataSubjectRequest
    ) -> DataSubjectRequest | None:
        orm_obj = await self._session.get(DataSubjectRequestModel, request.id)
        if orm_obj is None:
            return None
        orm_obj.request_type = request.request_type
        orm_obj.subject_email = request.subject_email
        orm_obj.subject_domain = request.subject_domain
        orm_obj.subject_name = request.subject_name
        orm_obj.status = request.status
        orm_obj.handled_by_user_id = request.handled_by_user_id
        orm_obj.notes = request.notes
        orm_obj.result_summary = request.result_summary
        orm_obj.completed_at = request.completed_at
        await self._session.flush()
        await self._session.refresh(orm_obj)
        return self._to_entity(orm_obj)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        request_type: str | None = None,
    ) -> list[DataSubjectRequest]:
        stmt = select(DataSubjectRequestModel)
        if status is not None:
            stmt = stmt.where(DataSubjectRequestModel.status == status)
        if request_type is not None:
            stmt = stmt.where(DataSubjectRequestModel.request_type == request_type)
        stmt = stmt.order_by(DataSubjectRequestModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_entity(row) for row in result.scalars().all()]

    @staticmethod
    def _to_entity(orm_obj: DataSubjectRequestModel) -> DataSubjectRequest:
        return DataSubjectRequest(
            id=orm_obj.id,
            request_type=orm_obj.request_type,
            subject_email=orm_obj.subject_email,
            subject_domain=orm_obj.subject_domain,
            subject_name=orm_obj.subject_name,
            status=orm_obj.status,
            requested_by_user_id=orm_obj.requested_by_user_id,
            handled_by_user_id=orm_obj.handled_by_user_id,
            notes=orm_obj.notes,
            result_summary=orm_obj.result_summary,
            created_at=orm_obj.created_at,
            updated_at=orm_obj.updated_at,
            completed_at=orm_obj.completed_at,
        )
