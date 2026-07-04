"""Shared pytest fixtures and test doubles.

``FakeWorkflowRunRepository`` is an in-memory stand-in for
``WorkflowRunRepository`` (mirroring how ``MockLLMProvider`` stands in for a
real LLM provider elsewhere in this test suite). This project's DB-backed
repositories (companies, leads, ...) are exercised end-to-end via Docker
Compose against real PostgreSQL rather than through pytest, since none of the
Postgres-specific column types (JSONB, native UUID) have a lightweight
in-process equivalent to test against. Using a fake at the repository port
boundary keeps service- and API-level tests fast and dependency-free while
still exercising real business logic.
"""

from __future__ import annotations

import datetime
import uuid

from backend.domain.entities.workflow_run import WorkflowRun
from backend.domain.enums import WorkflowReviewStatus
from backend.domain.repositories.workflow_run_repository import WorkflowRunRepository


class FakeWorkflowRunRepository(WorkflowRunRepository):
    """In-memory ``WorkflowRunRepository`` test double. No database involved."""

    def __init__(self) -> None:
        self._runs: dict[uuid.UUID, WorkflowRun] = {}

    async def create(self, run: WorkflowRun) -> WorkflowRun:
        now = datetime.datetime.now(datetime.timezone.utc)
        stored = WorkflowRun(
            id=uuid.uuid4(),
            company_name=run.company_name,
            workflow_type=run.workflow_type,
            status=run.status,
            review_status=run.review_status,
            input_payload=run.input_payload,
            result_payload=run.result_payload,
            confidence_score=run.confidence_score,
            missing_information=run.missing_information,
            compliance_notes=run.compliance_notes,
            created_at=now,
            updated_at=now,
        )
        self._runs[stored.id] = stored
        return stored

    async def get_by_id(self, run_id: uuid.UUID) -> WorkflowRun | None:
        return self._runs.get(run_id)

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        company_name: str | None = None,
        review_status: WorkflowReviewStatus | None = None,
    ) -> list[WorkflowRun]:
        items = sorted(self._runs.values(), key=lambda run: run.created_at, reverse=True)
        if company_name:
            needle = company_name.lower()
            items = [run for run in items if needle in run.company_name.lower()]
        if review_status is not None:
            items = [run for run in items if run.review_status == review_status]
        return items[offset : offset + limit]

    async def update_review_status(
        self, run_id: uuid.UUID, review_status: WorkflowReviewStatus
    ) -> WorkflowRun | None:
        run = self._runs.get(run_id)
        if run is None:
            return None
        run.review_status = review_status
        run.updated_at = datetime.datetime.now(datetime.timezone.utc)
        return run
