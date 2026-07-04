import uuid
from datetime import datetime, timezone

from backend.domain.entities.workflow_run import WorkflowRun
from backend.domain.enums import WorkflowReviewStatus
from backend.infrastructure.database.models.workflow_run import WorkflowRunModel
from backend.infrastructure.repositories.workflow_run import (
    SQLAlchemyWorkflowRunRepository,
)


def test_workflow_run_defaults():
    run = WorkflowRun(
        company_name="Acme GmbH",
        status="completed",
        input_payload={"company_name": "Acme GmbH"},
        result_payload={"status": "completed"},
    )

    assert run.workflow_type == "sales"
    assert run.review_status == WorkflowReviewStatus.NEEDS_REVIEW
    assert run.missing_information == []
    assert run.compliance_notes == []
    assert run.confidence_score is None
    assert run.id is None


def test_workflow_run_review_status_has_five_allowed_values():
    values = {status.value for status in WorkflowReviewStatus}
    assert values == {
        "needs_review",
        "reviewed",
        "approved",
        "rejected",
        "archived",
    }


def test_repository_maps_orm_row_to_domain_entity():
    now = datetime.now(timezone.utc)
    orm_obj = WorkflowRunModel(
        id=uuid.uuid4(),
        company_name="Acme GmbH",
        workflow_type="sales",
        status="completed",
        review_status=WorkflowReviewStatus.APPROVED,
        input_payload={"company_name": "Acme GmbH"},
        result_payload={"status": "completed"},
        confidence_score=0.75,
        missing_information=["Employee count"],
        compliance_notes=["No email was sent."],
        created_at=now,
        updated_at=now,
    )

    entity = SQLAlchemyWorkflowRunRepository._to_entity(orm_obj)

    assert isinstance(entity, WorkflowRun)
    assert entity.id == orm_obj.id
    assert entity.company_name == "Acme GmbH"
    assert entity.workflow_type == "sales"
    assert entity.status == "completed"
    assert entity.review_status == WorkflowReviewStatus.APPROVED
    assert entity.confidence_score == 0.75
    assert entity.missing_information == ["Employee count"]
    assert entity.compliance_notes == ["No email was sent."]
    assert entity.created_at == now
    assert entity.updated_at == now


def test_approved_review_status_is_not_a_send_flag():
    # Documents the contract explicitly: "approved" is an internal marker,
    # never a send/outreach trigger. There is deliberately no field on
    # WorkflowRun that represents "sent" or "contacted".
    run = WorkflowRun(
        company_name="Acme GmbH",
        status="completed",
        input_payload={},
        result_payload={},
        review_status=WorkflowReviewStatus.APPROVED,
    )
    assert not hasattr(run, "sent")
    assert not hasattr(run, "contacted")
    assert not hasattr(run, "email_sent")
