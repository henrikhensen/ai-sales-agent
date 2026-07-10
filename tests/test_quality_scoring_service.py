"""Tests for QualityScoringService using in-memory fakes — no real
database, no external calls, no LLM call unless a fake provider is passed.
"""

import uuid

from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.compliance.schemas import CreateDoNotContactRequest
from backend.domain.entities.company import Company
from backend.domain.entities.email_draft import EmailDraft
from backend.domain.entities.lead_candidate import LeadCandidate
from backend.domain.entities.outreach_queue_item import OutreachQueueItem
from backend.domain.entities.qualification_result import QualificationResult
from backend.domain.entities.reply import Reply
from backend.domain.entities.workflow_run import WorkflowRun
from tests.conftest import (
    FakeCompanyRepository,
    FakeDoNotContactRepository,
    FakeEmailDraftRepository,
    FakeLeadCandidateRepository,
    FakeOutreachQueueItemRepository,
    FakeQualificationResultRepository,
    FakeReplyRepository,
    FakeWorkflowRunRepository,
    build_fake_quality_scoring_service,
)


async def test_score_email_draft_with_good_content_scores_well():
    companies = FakeCompanyRepository()
    company = await companies.create(Company(name="Acme GmbH", domain="acme.example"))
    drafts = FakeEmailDraftRepository()
    draft = await drafts.create(
        EmailDraft(
            company_id=company.id,
            email_body=(
                "Hallo, ich habe gesehen, dass Acme GmbH im Bereich Logistik "
                "wächst. Hätten Sie Interesse an einem kurzen Gespräch, um zu "
                "sehen ob unser Angebot passt?"
            ),
            subject_lines=["Kurze Frage zu Acme GmbH"],
        )
    )
    service = build_fake_quality_scoring_service(
        companies=companies, email_drafts=drafts
    )
    score = await service.auto_score("email_draft", draft.id)
    assert score is not None
    assert score.score_level in ("good", "excellent", "acceptable")
    assert "do_not_contact" not in " ".join(score.compliance_flags)


async def test_score_email_draft_blocked_by_do_not_contact_is_blocked_level():
    companies = FakeCompanyRepository()
    company = await companies.create(Company(name="Blocked Co", domain="blocked.example"))
    compliance_service = DoNotContactService(FakeDoNotContactRepository())
    await compliance_service.create_entry(
        CreateDoNotContactRequest(domain="blocked.example", reason="Opt-out"),
        created_by_user_id=None,
    )
    drafts = FakeEmailDraftRepository()
    draft = await drafts.create(
        EmailDraft(
            company_id=company.id,
            email_body="Hallo, kurze Frage zu Ihrem Unternehmen. Interesse an einem Call?",
            subject_lines=["Frage"],
        )
    )
    service = build_fake_quality_scoring_service(
        companies=companies,
        email_drafts=drafts,
        compliance=compliance_service,
    )
    score = await service.auto_score("email_draft", draft.id)
    assert score is not None
    assert score.score_level == "blocked"
    assert score.score_total <= 20
    assert any("do_not_contact" in flag for flag in score.compliance_flags)


async def test_score_email_draft_missing_draft_returns_poor_with_warning():
    service = build_fake_quality_scoring_service()
    score = await service.auto_score("email_draft", uuid.uuid4())
    assert score is not None
    assert score.score_level == "poor"
    assert score.warnings


async def test_score_workflow_run_blocked_status_is_blocked_level():
    workflow_runs = FakeWorkflowRunRepository()
    run = await workflow_runs.create(
        WorkflowRun(company_name="Acme", status="blocked", input_payload={}, result_payload={})
    )
    service = build_fake_quality_scoring_service(workflow_runs=workflow_runs)
    score = await service.auto_score("workflow_run", run.id)
    assert score is not None
    assert score.score_level == "blocked"


async def test_score_workflow_run_completed_with_high_confidence_scores_well():
    workflow_runs = FakeWorkflowRunRepository()
    run = await workflow_runs.create(
        WorkflowRun(
            company_name="Acme",
            status="completed",
            input_payload={},
            result_payload={"website_research_used": True},
            confidence_score=0.9,
            email_draft_id=uuid.uuid4(),
        )
    )
    service = build_fake_quality_scoring_service(workflow_runs=workflow_runs)
    score = await service.auto_score("workflow_run", run.id)
    assert score is not None
    assert score.score_total > 50


async def test_score_lead_candidate_blocked_do_not_contact():
    candidates = FakeLeadCandidateRepository()
    candidate = await candidates.create(
        LeadCandidate(
            sourcing_run_id=uuid.uuid4(),
            campaign_id=uuid.uuid4(),
            company_name="Acme",
            do_not_contact_status="blocked",
        )
    )
    service = build_fake_quality_scoring_service(lead_candidates=candidates)
    score = await service.auto_score("lead_candidate", candidate.id)
    assert score is not None
    assert score.score_level == "blocked"


async def test_score_qualification_result_uses_compliance_status():
    results = FakeQualificationResultRepository()
    result = await results.create(
        QualificationResult(
            qualification_run_id=uuid.uuid4(),
            qualification_score=80,
            qualification_level="high",
            compliance_status="blocked",
        )
    )
    service = build_fake_quality_scoring_service(qualification_results=results)
    score = await service.auto_score("qualification_result", result.id)
    assert score is not None
    assert score.score_level == "blocked"


async def test_score_outreach_queue_item_with_last_error_lowers_score():
    items = FakeOutreachQueueItemRepository()
    item = await items.create(
        OutreachQueueItem(
            campaign_id=uuid.uuid4(),
            qualification_score=90,
            qualification_level="high",
            queue_status="ready_for_workflow",
            last_error="Provider timeout",
        )
    )
    service = build_fake_quality_scoring_service(outreach_queue_items=items)
    score = await service.auto_score("outreach_queue_item", item.id)
    assert score is not None
    assert score.score_total < 90


async def test_score_reply_low_confidence_adds_warning():
    replies = FakeReplyRepository()
    reply = await replies.create(
        Reply(
            provider="mock",
            provider_message_id="msg-1",
            from_email="lead@example.com",
            received_at=None,
            confidence_score=0.2,
        )
    )
    service = build_fake_quality_scoring_service(replies=replies)
    score = await service.auto_score("reply", reply.id)
    assert score is not None
    assert any("confidence" in w.lower() for w in score.warnings)


async def test_auto_score_never_raises_on_scoring_failure(monkeypatch):
    service = build_fake_quality_scoring_service()

    async def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "_score_email_draft", _boom)
    result = await service.auto_score("email_draft", uuid.uuid4())
    assert result is None


async def test_llm_advice_returns_none_when_disabled():
    service = build_fake_quality_scoring_service()
    advice = await service.get_llm_advice("email_draft", uuid.uuid4())
    assert advice is None
