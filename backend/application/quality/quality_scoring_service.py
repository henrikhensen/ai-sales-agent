"""Quality Scoring: rule-based evaluation of drafts, workflows, leads,
qualification results, outreach queue items, and replies.

Rule-based scoring is always available and never needs an LLM or network
call. Scores are decision support only — never a guarantee, never a legal
clearance, and never a substitute for Human Review or Do-not-contact.
``score_level="blocked"`` is reserved for entities blocked by Do-not-
contact or another compliance gate; a blocked entity can never also score
as good, regardless of everything else. When data needed for a criterion
is missing, this reports a warning rather than fabricating an assessment.

The optional LLM Quality Advisor (used only when
``QUALITY_SCORING_USE_LLM=true``) is a strictly additive enhancement on
top of the rule-based score — see :meth:`QualityScoringService.get_llm_advice`.
It sends only a short, bounded excerpt (never a full email/reply body or
a full LLM prompt log) and never a secret. If it's disabled, unavailable,
or fails for any reason, the rule-based score is used unchanged.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.application.audit.audit_log_service import AuditLogService
from backend.application.compliance.do_not_contact_service import DoNotContactService
from backend.application.quality.quality_score_schemas import (
    CreateQualityScoreRequest,
    QualityScoreListResponse,
    QualityScoreResponse,
)
from backend.domain.entities.quality_score import QualityScore
from backend.domain.exceptions import QualityScoreNotFoundError
from backend.domain.repositories.company_repository import CompanyRepository
from backend.domain.repositories.email_draft_repository import EmailDraftRepository
from backend.domain.repositories.icp_profile_repository import ICPProfileRepository
from backend.domain.repositories.lead_candidate_repository import (
    LeadCandidateRepository,
)
from backend.domain.repositories.offer_profile_repository import (
    OfferProfileRepository,
)
from backend.domain.repositories.outreach_queue_item_repository import (
    OutreachQueueItemRepository,
)
from backend.domain.repositories.qualification_result_repository import (
    QualificationResultRepository,
)
from backend.domain.repositories.quality_score_repository import (
    QualityScoreRepository,
)
from backend.domain.repositories.reply_repository import ReplyRepository
from backend.domain.repositories.user_feedback_repository import (
    UserFeedbackRepository,
)
from backend.domain.repositories.workflow_run_repository import WorkflowRunRepository
from backend.infrastructure.llm.base import LLMError, LLMProvider
from backend.shared.config import Settings

logger = logging.getLogger("backend.quality.scoring")

_MAX_LLM_EXCERPT_CHARS = 600

_AGGRESSIVE_PHRASES = (
    "jetzt sofort",
    "nur heute",
    "letzte chance",
    "verpassen sie nicht",
    "act now",
    "last chance",
    "don't miss out",
    "buy now",
    "limited time only",
)


def _score_level(score_total: int) -> str:
    if score_total >= 90:
        return "excellent"
    if score_total >= 75:
        return "good"
    if score_total >= 60:
        return "acceptable"
    if score_total >= 40:
        return "weak"
    return "poor"


def _clamp(value: int) -> int:
    return max(0, min(100, value))


class QualityScoringService:
    def __init__(
        self,
        quality_scores: QualityScoreRepository,
        email_drafts: EmailDraftRepository,
        workflow_runs: WorkflowRunRepository,
        companies: CompanyRepository,
        lead_candidates: LeadCandidateRepository,
        qualification_results: QualificationResultRepository,
        outreach_queue_items: OutreachQueueItemRepository,
        replies: ReplyRepository,
        offer_profiles: OfferProfileRepository,
        icp_profiles: ICPProfileRepository,
        compliance: DoNotContactService,
        user_feedback: UserFeedbackRepository,
        audit: AuditLogService,
        settings: Settings,
        llm_provider: LLMProvider | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        # Optional: only used by auto_score's except-block below to roll
        # back a request-scoped session after a caught failure, so a
        # transient error here (e.g. a DB hiccup mid-flush) can never leave
        # the session unusable for whatever the caller does next in the
        # same request — matching this method's own documented guarantee
        # that a scoring failure must never break the action it's
        # observing. None (the default) in every existing call site/test
        # that constructs this service without a session keeps behavior
        # unchanged there.
        self._session = session
        self._quality_scores = quality_scores
        self._email_drafts = email_drafts
        self._workflow_runs = workflow_runs
        self._companies = companies
        self._lead_candidates = lead_candidates
        self._qualification_results = qualification_results
        self._outreach_queue_items = outreach_queue_items
        self._replies = replies
        self._offer_profiles = offer_profiles
        self._icp_profiles = icp_profiles
        self._compliance = compliance
        self._user_feedback = user_feedback
        self._audit = audit
        self._settings = settings
        self._llm_provider = llm_provider

    # -- public API -----------------------------------------------------------------

    async def score_entity(
        self,
        request: CreateQualityScoreRequest,
        actor_user_id: UUID | None,
        actor_role: str | None,
        http_request: Request | None = None,
    ) -> QualityScoreResponse:
        score = await self._compute(
            request.entity_type, request.entity_id, evaluated_by_user_id=actor_user_id
        )
        stored = await self._quality_scores.create(score)
        await self._audit.record(
            action="quality_score_created",
            result="success",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            entity_type=request.entity_type,
            entity_id=request.entity_id,
            metadata={
                "score_total": stored.score_total,
                "score_level": stored.score_level,
            },
            request=http_request,
        )
        return QualityScoreResponse.model_validate(stored)

    async def get_score(self, score_id: UUID) -> QualityScoreResponse:
        score = await self._quality_scores.get_by_id(score_id)
        if score is None:
            raise QualityScoreNotFoundError(score_id)
        return QualityScoreResponse.model_validate(score)

    async def list_scores(
        self,
        limit: int = 100,
        offset: int = 0,
        entity_type: str | None = None,
        score_level: str | None = None,
    ) -> QualityScoreListResponse:
        items = await self._quality_scores.list(
            limit=limit, offset=offset, entity_type=entity_type, score_level=score_level
        )
        return QualityScoreListResponse(
            items=[QualityScoreResponse.model_validate(s) for s in items],
            limit=limit,
            offset=offset,
        )

    async def get_entity_scores(
        self, entity_type: str, entity_id: UUID, limit: int = 100, offset: int = 0
    ) -> QualityScoreListResponse:
        items = await self._quality_scores.list_for_entity(
            entity_type, entity_id, limit=limit, offset=offset
        )
        return QualityScoreListResponse(
            items=[QualityScoreResponse.model_validate(s) for s in items],
            limit=limit,
            offset=offset,
        )

    async def auto_score(
        self, entity_type: str, entity_id: UUID
    ) -> QualityScore | None:
        """Best-effort scoring used by integration points (Sales Workflow
        completion, ...). Never raises — a scoring failure only ever
        produces a log warning, since quality scoring must never break the
        action it's observing."""
        if not self._settings.quality_scoring_enabled:
            return None
        try:
            score = await self._compute(entity_type, entity_id, evaluated_by_user_id=None)
            return await self._quality_scores.create(score)
        except Exception:
            logger.warning(
                "auto quality scoring failed for entity_type=%s entity_id=%s",
                entity_type,
                entity_id,
                exc_info=True,
            )
            if self._session is not None:
                try:
                    await self._session.rollback()
                except Exception:
                    logger.warning(
                        "failed to roll back session after a failed auto "
                        "quality scoring attempt",
                        exc_info=True,
                    )
            return None

    # -- dispatch to per-entity scorers ----------------------------------------------

    async def _compute(
        self, entity_type: str, entity_id: UUID, *, evaluated_by_user_id: UUID | None
    ) -> QualityScore:
        handler = {
            "email_draft": self._score_email_draft,
            "workflow_run": self._score_workflow_run,
            "lead_candidate": self._score_lead_candidate,
            "qualification_result": self._score_qualification_result,
            "outreach_queue_item": self._score_outreach_queue_item,
            "reply": self._score_reply,
        }.get(entity_type)
        if handler is None:
            return QualityScore(
                entity_type=entity_type,
                entity_id=entity_id,
                score_total=0,
                score_level="poor",
                warnings=[f"Scoring for entity_type '{entity_type}' is not supported."],
                evaluated_by="user" if evaluated_by_user_id else "system",
                evaluated_by_user_id=evaluated_by_user_id,
                provider=self._settings.quality_scoring_provider,
            )
        score = await handler(entity_id)
        score.evaluated_by = "user" if evaluated_by_user_id else "system"
        score.evaluated_by_user_id = evaluated_by_user_id
        score.provider = self._settings.quality_scoring_provider
        return score

    # -- email draft ------------------------------------------------------------------

    async def _score_email_draft(self, email_draft_id: UUID) -> QualityScore:
        draft = await self._email_drafts.get(email_draft_id)
        if draft is None:
            return QualityScore(
                entity_type="email_draft",
                entity_id=email_draft_id,
                score_total=0,
                score_level="poor",
                warnings=["Email draft not found — cannot be scored."],
            )

        breakdown: dict[str, Any] = {}
        strengths: list[str] = []
        weaknesses: list[str] = []
        warnings: list[str] = []
        recommendations: list[str] = []
        compliance_flags: list[str] = []
        points = 50  # neutral baseline

        company = await self._companies.get(draft.company_id)
        company_name = company.name if company is not None else None

        # Do-not-contact / compliance always wins — checked first.
        dnc = await self._compliance.check(
            domain=company.domain if company else None,
            company_name=company_name,
        )
        if dnc.is_blocked:
            compliance_flags.append(f"do_not_contact: matched by {dnc.matched_by or 'unknown'}")

        body = draft.email_body or ""
        word_count = len(body.split())
        breakdown["word_count"] = word_count
        if word_count == 0:
            weaknesses.append("Email body is empty.")
            points -= 40
        elif word_count < 40:
            weaknesses.append("Email body is very short — may lack substance.")
            points -= 15
        elif word_count > 350:
            weaknesses.append("Email body is long — consider shortening it.")
            points -= 10
        else:
            strengths.append("Email body length is within a reasonable range.")
            points += 10

        if company_name and company_name.lower() in body.lower():
            strengths.append("Mentions the company by name (personalized).")
            points += 15
            breakdown["personalization"] = "company_name_present"
        else:
            weaknesses.append("Does not clearly mention the company by name.")
            recommendations.append("Reference the company or a specific detail about it.")
            points -= 5

        has_question = "?" in body
        cta_keywords = ("interesse", "termin", "gespräch", "call", "meeting", "demo")
        has_cta_keyword = any(keyword in body.lower() for keyword in cta_keywords)
        if has_question or has_cta_keyword:
            strengths.append("Contains a recognizable call-to-action.")
            points += 15
            breakdown["cta_present"] = True
        else:
            weaknesses.append("No clear call-to-action detected.")
            recommendations.append(
                "Add a concrete, low-friction call-to-action (e.g. a short question)."
            )
            breakdown["cta_present"] = False
            points -= 15

        matched_aggressive = [p for p in _AGGRESSIVE_PHRASES if p in body.lower()]
        if matched_aggressive:
            weaknesses.append("Contains aggressive/high-pressure language.")
            recommendations.append("Remove urgency/pressure phrasing; keep the tone low-key.")
            breakdown["aggressive_phrases"] = matched_aggressive
            points -= 20
        else:
            breakdown["aggressive_phrases"] = []

        exclamation_count = body.count("!")
        if exclamation_count > 2:
            weaknesses.append("Excessive use of exclamation marks.")
            points -= 5

        if not draft.subject_lines:
            warnings.append("No subject line was recorded for this draft.")
            points -= 5
        else:
            breakdown["subject_line_count"] = len(draft.subject_lines)

        # Enrich with the originating workflow run's own recorded output,
        # when available — never fabricated, only what was already stored.
        offer_forbidden_hits: list[str] = []
        if draft.workflow_run_id is not None:
            run = await self._workflow_runs.get_by_id(draft.workflow_run_id)
            if run is not None:
                payload = run.result_payload or {}
                offer_profile_id = payload.get("offer_profile_id")
                icp_fit_level = payload.get("icp_fit_level")
                claims_to_verify = (payload.get("email_draft") or {}).get(
                    "claims_to_verify"
                ) or []
                if claims_to_verify:
                    warnings.append(
                        f"{len(claims_to_verify)} claim(s) still need human verification."
                    )
                if icp_fit_level:
                    breakdown["icp_fit_level"] = icp_fit_level
                    if icp_fit_level in ("weak", "not_fit"):
                        weaknesses.append(f"ICP fit is '{icp_fit_level}' for this lead.")
                        points -= 10
                    elif icp_fit_level in ("strong", "good"):
                        strengths.append(f"ICP fit is '{icp_fit_level}'.")
                        points += 10
                if offer_profile_id:
                    try:
                        offer = await self._offer_profiles.get_by_id(UUID(offer_profile_id))
                    except (ValueError, TypeError):
                        offer = None
                    if offer is not None:
                        breakdown["offer_used"] = True
                        for claim in offer.forbidden_claims:
                            if claim.lower() in body.lower():
                                offer_forbidden_hits.append(claim)
                    else:
                        warnings.append("Linked offer profile could not be loaded.")
                else:
                    warnings.append("No offer profile was linked to this draft's workflow.")
            else:
                warnings.append("Linked workflow run could not be found.")
        else:
            warnings.append(
                "No linked workflow run — personalization/offer/ICP context cannot be verified."
            )

        if offer_forbidden_hits:
            compliance_flags.append(
                "forbidden_claims: " + "; ".join(offer_forbidden_hits)
            )
            weaknesses.append("Contains a claim explicitly forbidden by the offer profile.")
            points -= 40

        blocking_count = await self._user_feedback.count_blocking_for_entity(
            "email_draft", email_draft_id
        )
        if blocking_count:
            warnings.append(
                f"{blocking_count} open blocking feedback item(s) exist for this draft."
            )
            points -= 15

        score_total = _clamp(points)
        score_level = "blocked" if (dnc.is_blocked or offer_forbidden_hits) else _score_level(
            score_total
        )
        if score_level == "blocked":
            score_total = min(score_total, 20)

        return QualityScore(
            entity_type="email_draft",
            entity_id=email_draft_id,
            email_draft_id=email_draft_id,
            company_id=draft.company_id,
            lead_id=draft.lead_id,
            workflow_run_id=draft.workflow_run_id,
            score_total=score_total,
            score_level=score_level,
            score_breakdown=breakdown,
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=warnings,
            recommended_improvements=recommendations,
            compliance_flags=compliance_flags,
        )

    # -- workflow run -------------------------------------------------------------

    async def _score_workflow_run(self, workflow_run_id: UUID) -> QualityScore:
        run = await self._workflow_runs.get_by_id(workflow_run_id)
        if run is None:
            return QualityScore(
                entity_type="workflow_run",
                entity_id=workflow_run_id,
                score_total=0,
                score_level="poor",
                warnings=["Workflow run not found — cannot be scored."],
            )

        breakdown: dict[str, Any] = {}
        strengths: list[str] = []
        weaknesses: list[str] = []
        warnings: list[str] = []
        recommendations: list[str] = []
        compliance_flags: list[str] = []
        points = 50

        if run.status == "blocked":
            compliance_flags.append("do_not_contact: workflow blocked")

        confidence = run.confidence_score or 0.0
        breakdown["confidence_score"] = confidence
        points += int((confidence - 0.5) * 60)

        payload = run.result_payload or {}
        website_research_used = payload.get("website_research_used", False)
        breakdown["website_research_used"] = website_research_used
        if website_research_used:
            strengths.append("Website research was used to ground this run.")
            points += 10

        if run.email_draft_id is not None:
            strengths.append("An email draft was produced.")
            points += 10
        elif run.status != "blocked":
            weaknesses.append("No email draft was produced for this run.")
            points -= 15

        missing_count = len(run.missing_information or [])
        breakdown["missing_information_count"] = missing_count
        if missing_count:
            weaknesses.append(f"{missing_count} item(s) of missing information were noted.")
            recommendations.append("Fill in the missing information before relying on this run.")
            points -= min(missing_count * 5, 25)

        if run.review_status.value == "approved":
            strengths.append("This run has been human-approved.")
            points += 10
        elif run.review_status.value == "rejected":
            weaknesses.append("This run was rejected in Human Review.")
            points -= 25

        score_total = _clamp(points)
        score_level = "blocked" if run.status == "blocked" else _score_level(score_total)
        if score_level == "blocked":
            score_total = min(score_total, 20)

        return QualityScore(
            entity_type="workflow_run",
            entity_id=workflow_run_id,
            workflow_run_id=workflow_run_id,
            company_id=run.company_id,
            lead_id=run.lead_id,
            score_total=score_total,
            score_level=score_level,
            score_breakdown=breakdown,
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=warnings,
            recommended_improvements=recommendations,
            compliance_flags=compliance_flags,
        )

    # -- lead candidate ---------------------------------------------------------------

    async def _score_lead_candidate(self, lead_candidate_id: UUID) -> QualityScore:
        candidate = await self._lead_candidates.get_by_id(lead_candidate_id)
        if candidate is None:
            return QualityScore(
                entity_type="lead_candidate",
                entity_id=lead_candidate_id,
                score_total=0,
                score_level="poor",
                warnings=["Lead candidate not found — cannot be scored."],
            )

        breakdown: dict[str, Any] = {}
        strengths: list[str] = []
        weaknesses: list[str] = []
        warnings: list[str] = []
        recommendations: list[str] = []
        compliance_flags: list[str] = []
        points = 40

        if candidate.do_not_contact_status == "blocked":
            compliance_flags.append("do_not_contact: blocked")
        if candidate.duplicate_status == "duplicate":
            weaknesses.append("Marked as a duplicate of an existing lead/company.")
            points -= 15

        if candidate.icp_fit_score is not None:
            breakdown["icp_fit_score"] = candidate.icp_fit_score
            points += int((candidate.icp_fit_score - 50) * 0.6)
        else:
            warnings.append("No ICP fit score recorded yet.")

        if candidate.confidence_score is not None:
            breakdown["confidence_score"] = candidate.confidence_score
            points += int((candidate.confidence_score - 0.5) * 30)

        if candidate.public_contact_email:
            strengths.append("A public contact email is on file.")
            points += 10
        else:
            warnings.append("No public contact email on file yet.")

        signal_balance = len(candidate.matched_signals) - len(candidate.negative_signals)
        breakdown["signal_balance"] = signal_balance
        points += signal_balance * 3
        if candidate.negative_signals:
            weaknesses.append(
                f"{len(candidate.negative_signals)} negative signal(s) recorded."
            )
        if candidate.matched_signals:
            strengths.append(f"{len(candidate.matched_signals)} matched ICP signal(s).")

        if not candidate.industry or not candidate.location:
            warnings.append("Industry or location data is incomplete.")
            recommendations.append("Enrich missing company data before qualifying further.")
            points -= 5

        score_total = _clamp(points)
        score_level = (
            "blocked" if candidate.do_not_contact_status == "blocked" else _score_level(score_total)
        )
        if score_level == "blocked":
            score_total = min(score_total, 20)

        return QualityScore(
            entity_type="lead_candidate",
            entity_id=lead_candidate_id,
            lead_candidate_id=lead_candidate_id,
            score_total=score_total,
            score_level=score_level,
            score_breakdown=breakdown,
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=warnings,
            recommended_improvements=recommendations,
            compliance_flags=compliance_flags,
        )

    # -- qualification result -----------------------------------------------------

    async def _score_qualification_result(self, result_id: UUID) -> QualityScore:
        result = await self._qualification_results.get_by_id(result_id)
        if result is None:
            return QualityScore(
                entity_type="qualification_result",
                entity_id=result_id,
                score_total=0,
                score_level="poor",
                warnings=["Qualification result not found — cannot be scored."],
            )

        breakdown: dict[str, Any] = {"qualification_level": result.qualification_level}
        strengths: list[str] = []
        weaknesses: list[str] = []
        warnings: list[str] = []
        recommendations: list[str] = []
        compliance_flags: list[str] = []

        blocked = (
            result.do_not_contact_status == "blocked" or result.compliance_status != "clear"
        )
        if blocked:
            compliance_flags.append(
                f"compliance_status={result.compliance_status}, "
                f"do_not_contact_status={result.do_not_contact_status}"
            )

        points = result.qualification_score
        if result.duplicate_status == "duplicate":
            weaknesses.append("Marked as a duplicate.")
            points -= 15
        if result.missing_data:
            weaknesses.append(f"{len(result.missing_data)} missing data point(s).")
            recommendations.append("Fill in missing data to raise confidence in this result.")
            points -= min(len(result.missing_data) * 5, 20)
        if result.disqualification_reason:
            weaknesses.append(f"Disqualification reason: {result.disqualification_reason}")
            points -= 30
        if result.positive_signals:
            strengths.append(f"{len(result.positive_signals)} positive signal(s).")
        if result.confidence_score is not None:
            breakdown["confidence_score"] = result.confidence_score

        score_total = _clamp(points)
        score_level = "blocked" if blocked else _score_level(score_total)
        if score_level == "blocked":
            score_total = min(score_total, 20)

        return QualityScore(
            entity_type="qualification_result",
            entity_id=result_id,
            qualification_result_id=result_id,
            lead_id=result.lead_id,
            lead_candidate_id=result.lead_candidate_id,
            company_id=result.company_id,
            score_total=score_total,
            score_level=score_level,
            score_breakdown=breakdown,
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=warnings,
            recommended_improvements=recommendations,
            compliance_flags=compliance_flags,
        )

    # -- outreach queue item --------------------------------------------------------

    async def _score_outreach_queue_item(self, item_id: UUID) -> QualityScore:
        item = await self._outreach_queue_items.get_by_id(item_id)
        if item is None:
            return QualityScore(
                entity_type="outreach_queue_item",
                entity_id=item_id,
                score_total=0,
                score_level="poor",
                warnings=["Outreach queue item not found — cannot be scored."],
            )

        breakdown: dict[str, Any] = {"queue_status": item.queue_status}
        strengths: list[str] = []
        weaknesses: list[str] = []
        warnings: list[str] = []
        recommendations: list[str] = []
        compliance_flags: list[str] = []

        blocked = item.do_not_contact_status == "blocked" or item.compliance_status != "clear"
        if blocked:
            compliance_flags.append(
                f"compliance_status={item.compliance_status}, "
                f"do_not_contact_status={item.do_not_contact_status}"
            )

        points = item.qualification_score
        if item.email_draft_id is not None:
            strengths.append("An email draft has been prepared for this item.")
            points += 10
        else:
            warnings.append("No email draft prepared yet.")
        if item.last_error:
            weaknesses.append(f"Last action reported an error: {item.last_error}")
            points -= 15
        if item.duplicate_status == "duplicate":
            weaknesses.append("Marked as a duplicate.")
            points -= 10
        if item.queue_status in ("blocked", "rejected", "cancelled", "failed"):
            weaknesses.append(f"Queue status is '{item.queue_status}'.")
            points -= 10

        blocking_count = await self._user_feedback.count_blocking_for_entity(
            "outreach_queue_item", item_id
        )
        if blocking_count:
            warnings.append(
                f"{blocking_count} open blocking feedback item(s) exist for this item."
            )
            recommendations.append("Resolve blocking feedback before dispatching.")
            points -= 15

        score_total = _clamp(points)
        score_level = "blocked" if blocked else _score_level(score_total)
        if score_level == "blocked":
            score_total = min(score_total, 20)

        return QualityScore(
            entity_type="outreach_queue_item",
            entity_id=item_id,
            outreach_queue_item_id=item_id,
            lead_id=item.lead_id,
            company_id=item.company_id,
            lead_candidate_id=item.lead_candidate_id,
            qualification_result_id=item.qualification_result_id,
            email_draft_id=item.email_draft_id,
            score_total=score_total,
            score_level=score_level,
            score_breakdown=breakdown,
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=warnings,
            recommended_improvements=recommendations,
            compliance_flags=compliance_flags,
        )

    # -- reply ----------------------------------------------------------------------

    async def _score_reply(self, reply_id: UUID) -> QualityScore:
        reply = await self._replies.get(reply_id)
        if reply is None:
            return QualityScore(
                entity_type="reply",
                entity_id=reply_id,
                score_total=0,
                score_level="poor",
                warnings=["Reply not found — cannot be scored."],
            )

        breakdown: dict[str, Any] = {}
        strengths: list[str] = []
        weaknesses: list[str] = []
        warnings: list[str] = []
        recommendations: list[str] = []
        points = 60

        if reply.confidence_score is not None:
            breakdown["confidence_score"] = reply.confidence_score
            if reply.confidence_score < 0.5:
                warnings.append(
                    "Low-confidence classification — the detected intent/category "
                    "should be reviewed before acting on it."
                )
                recommendations.append(
                    "Give feedback if the detected category/intent looks wrong."
                )
                points -= 20
            else:
                strengths.append("Classification confidence is reasonable.")
                points += 10
        else:
            warnings.append("No confidence score recorded for this reply's classification.")
            points -= 10

        if reply.last_error:
            weaknesses.append(f"Reply analysis reported an error: {reply.last_error}")
            points -= 20

        if not reply.body_preview and not reply.body_text:
            warnings.append("No body content stored for this reply.")
            points -= 15

        blocking_count = await self._user_feedback.count_blocking_for_entity(
            "reply", reply_id
        )
        if blocking_count:
            warnings.append(
                f"{blocking_count} open blocking feedback item(s) exist for this reply "
                "(e.g. a miscategorized intent)."
            )
            points -= 15

        score_total = _clamp(points)
        return QualityScore(
            entity_type="reply",
            entity_id=reply_id,
            reply_id=reply_id,
            lead_id=reply.lead_id,
            company_id=reply.company_id,
            score_total=score_total,
            score_level=_score_level(score_total),
            score_breakdown=breakdown,
            strengths=strengths,
            weaknesses=weaknesses,
            warnings=warnings,
            recommended_improvements=recommendations,
        )

    # -- optional LLM Quality Advisor ------------------------------------------------

    async def get_llm_advice(
        self, entity_type: str, entity_id: UUID
    ) -> dict[str, Any] | None:
        """Best-effort, additive LLM advice on top of the rule-based score.

        Returns None (never raises) if LLM advice is disabled, the entity
        can't be found, or the call fails for any reason — callers must
        treat this as purely optional enrichment. Uses the central LLM
        provider factory (Mock by default); only sends a short, bounded
        excerpt, never a full email/reply body, never a secret.
        """
        if not self._settings.quality_scoring_use_llm or self._llm_provider is None:
            return None
        try:
            excerpt = await self._build_excerpt(entity_type, entity_id)
            if excerpt is None:
                return None
            schema = {
                "type": "object",
                "properties": {
                    "weaknesses": {"type": "array", "items": {"type": "string"}},
                    "improvements": {"type": "array", "items": {"type": "string"}},
                    "cta_ideas": {"type": "array", "items": {"type": "string"}},
                    "compliance_notes": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["weaknesses", "improvements"],
            }
            result = await self._llm_provider.generate_json(
                system=(
                    "You are a sales email quality advisor. Analyze the excerpt "
                    "below and suggest concrete improvements. Never invent facts "
                    "about the company or contact. Never suggest a guaranteed "
                    "outcome or an unverifiable claim. Be concise."
                ),
                prompt=f"Excerpt (entity_type={entity_type}):\n{excerpt}",
                schema=schema,
                max_tokens=400,
            )
            return result
        except LLMError:
            logger.warning(
                "LLM quality advisor failed for entity_type=%s entity_id=%s",
                entity_type,
                entity_id,
                exc_info=True,
            )
            return None
        except Exception:
            logger.warning(
                "LLM quality advisor failed unexpectedly for entity_type=%s entity_id=%s",
                entity_type,
                entity_id,
                exc_info=True,
            )
            return None

    async def _build_excerpt(self, entity_type: str, entity_id: UUID) -> str | None:
        """Build a short, bounded excerpt for the LLM advisor — never a
        full email/reply body."""
        if entity_type == "email_draft":
            draft = await self._email_drafts.get(entity_id)
            if draft is None:
                return None
            return (draft.email_body or "")[:_MAX_LLM_EXCERPT_CHARS]
        if entity_type == "reply":
            reply = await self._replies.get(entity_id)
            if reply is None:
                return None
            text = reply.body_preview or reply.body_text or ""
            return text[:_MAX_LLM_EXCERPT_CHARS]
        return None
