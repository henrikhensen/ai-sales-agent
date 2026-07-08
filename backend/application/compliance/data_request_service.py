"""Data Subject Requests: tracked requests from or about a data subject.

Recording a request never performs the requested action automatically and
never sends an email to the subject. Export and anonymize-preparation are
explicit, separate, admin-triggered follow-up actions. Completing a
``do_not_contact``-type request creates a do-not-contact entry — it still
never contacts anyone; it only ever blocks future outreach.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.compliance.data_export_schemas import DataExportRequest
from backend.application.compliance.data_export_service import DataExportService
from backend.application.compliance.data_request_schemas import (
    CompleteDataRequestRequest,
    CreateDataSubjectRequestRequest,
    DataSubjectRequestDetailResponse,
    DataSubjectRequestListResponse,
    DataSubjectRequestResponse,
    PrepareAnonymizeDataRequestResponse,
    UpdateDataSubjectRequestRequest,
)
from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.compliance.schemas import CreateDoNotContactRequest
from backend.domain.entities.data_subject_request import DataSubjectRequest
from backend.domain.exceptions import DataSubjectRequestNotFoundError
from backend.domain.repositories.contact_repository import ContactRepository
from backend.domain.repositories.data_subject_request_repository import (
    DataSubjectRequestRepository,
)
from backend.domain.repositories.lead_candidate_repository import (
    LeadCandidateRepository,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DataRequestService:
    def __init__(
        self,
        requests: DataSubjectRequestRepository,
        contacts: ContactRepository,
        lead_candidates: LeadCandidateRepository,
        data_export: DataExportService,
        do_not_contact: DoNotContactService,
        audit: AuditLogService,
    ) -> None:
        self._requests = requests
        self._contacts = contacts
        self._lead_candidates = lead_candidates
        self._data_export = data_export
        self._do_not_contact = do_not_contact
        self._audit = audit

    async def create_request(
        self,
        request: CreateDataSubjectRequestRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> DataSubjectRequestResponse:
        created = await self._requests.create(
            DataSubjectRequest(
                request_type=request.request_type,
                subject_email=request.subject_email.lower()
                if request.subject_email
                else None,
                subject_domain=request.subject_domain.lower()
                if request.subject_domain
                else None,
                subject_name=request.subject_name,
                notes=request.notes,
                requested_by_user_id=actor_user_id,
            )
        )
        await self._audit.record(
            action="data_subject_request_created",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="data_subject_request",
            entity_id=created.id,
            metadata={"request_type": request.request_type},
            request=http_request,
        )
        return DataSubjectRequestResponse.model_validate(created)

    async def list_requests(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
        request_type: str | None = None,
    ) -> DataSubjectRequestListResponse:
        items = await self._requests.list(
            limit=limit, offset=offset, status=status, request_type=request_type
        )
        return DataSubjectRequestListResponse(
            items=[DataSubjectRequestResponse.model_validate(r) for r in items],
            limit=limit,
            offset=offset,
        )

    async def _get_or_404(self, request_id: UUID) -> DataSubjectRequest:
        request = await self._requests.get_by_id(request_id)
        if request is None:
            raise DataSubjectRequestNotFoundError(request_id)
        return request

    async def get_request(self, request_id: UUID) -> DataSubjectRequestResponse:
        request = await self._get_or_404(request_id)
        return DataSubjectRequestResponse.model_validate(request)

    async def update_request(
        self,
        request_id: UUID,
        payload: UpdateDataSubjectRequestRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> DataSubjectRequestResponse:
        request = await self._get_or_404(request_id)
        updates = payload.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            setattr(request, field_name, value)
        request.handled_by_user_id = actor_user_id or request.handled_by_user_id
        updated = await self._requests.update(request)
        assert updated is not None
        await self._audit.record(
            action="data_subject_request_updated",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="data_subject_request",
            entity_id=updated.id,
            metadata={"fields": list(updates.keys())},
            request=http_request,
        )
        return DataSubjectRequestResponse.model_validate(updated)

    async def export_for_request(
        self,
        request_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> DataSubjectRequestDetailResponse:
        request = await self._get_or_404(request_id)
        export = await self._data_export.export(
            DataExportRequest(
                email=request.subject_email,
                domain=request.subject_domain,
                name=request.subject_name,
            ),
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            http_request=http_request,
        )
        if request.status == "open":
            request.status = "in_progress"
            request.handled_by_user_id = actor_user_id or request.handled_by_user_id
            updated = await self._requests.update(request)
            assert updated is not None
            request = updated
        await self._audit.record(
            action="data_subject_request_export_executed",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="data_subject_request",
            entity_id=request.id,
            request=http_request,
        )
        return DataSubjectRequestDetailResponse(
            request=DataSubjectRequestResponse.model_validate(request), export=export
        )

    async def prepare_anonymize(
        self,
        request_id: UUID,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> PrepareAnonymizeDataRequestResponse:
        """Identify which records WOULD be affected — never anonymizes
        anything itself. Actually anonymizing/deleting data is a separate,
        explicit Data Retention run (see ``DataRetentionService``), started
        deliberately by an admin afterward."""
        request = await self._get_or_404(request_id)
        matched_contact_ids: list[UUID] = []
        matched_candidate_ids: list[UUID] = []

        if request.subject_email:
            candidates = await self._lead_candidates.list(limit=500)
            matched_candidate_ids = [
                c.id
                for c in candidates
                if c.public_contact_email
                and c.public_contact_email.lower() == request.subject_email
                and c.id is not None
            ]

        if request.status == "open":
            request.status = "in_progress"
            request.handled_by_user_id = actor_user_id or request.handled_by_user_id
            updated = await self._requests.update(request)
            assert updated is not None
            request = updated

        await self._audit.record(
            action="data_subject_request_anonymize_prepared",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="data_subject_request",
            entity_id=request.id,
            metadata={
                "matched_contact_ids": len(matched_contact_ids),
                "matched_candidate_ids": len(matched_candidate_ids),
            },
            request=http_request,
        )
        return PrepareAnonymizeDataRequestResponse(
            request=DataSubjectRequestResponse.model_validate(request),
            message=(
                "This lists potentially matching records only — nothing has "
                "been changed. Use Data Retention Policies (admin, with "
                "explicit confirmation) to actually anonymize or delete data."
            ),
            matched_lead_candidate_ids=matched_candidate_ids,
            matched_contact_ids=matched_contact_ids,
        )

    async def complete_request(
        self,
        request_id: UUID,
        payload: CompleteDataRequestRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> DataSubjectRequestResponse:
        request = await self._get_or_404(request_id)

        if request.request_type == "do_not_contact":
            await self._do_not_contact.create_entry(
                CreateDoNotContactRequest(
                    email=request.subject_email,
                    domain=request.subject_domain,
                    company_name=request.subject_name,
                    reason=f"Data subject request {request.id}: opt-out honored.",
                    source="data_subject_request",
                ),
                created_by_user_id=actor_user_id,
            )

        request.status = "completed"
        request.completed_at = _now()
        request.handled_by_user_id = actor_user_id or request.handled_by_user_id
        if payload.result_summary:
            request.result_summary = payload.result_summary
        updated = await self._requests.update(request)
        assert updated is not None
        await self._audit.record(
            action="data_subject_request_completed",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type="data_subject_request",
            entity_id=updated.id,
            metadata={"request_type": updated.request_type},
            request=http_request,
        )
        return DataSubjectRequestResponse.model_validate(updated)
