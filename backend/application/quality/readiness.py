"""Shared Beta Readiness computation, used by both the Quality Dashboard
and the Beta Test Dashboard so the two stay consistent.

'beta_ready' is an internal, technical signal only — it never means legal
clearance, and it never means the product is automatically market-ready.
See CUSTOMER_READINESS.md.
"""

from __future__ import annotations

from backend.application.quality.beta_test_schemas import BetaReadinessLevel
from backend.shared.config import Settings


def compute_beta_readiness(
    *,
    settings: Settings,
    average_quality_score: float | None,
    total_feedback_items: int,
    blocking_feedback_items: int,
    total_scores: int,
) -> tuple[BetaReadinessLevel, list[str], list[str]]:
    """Return ``(readiness_level, recommendations, warnings)``."""
    warnings: list[str] = []
    recommendations: list[str] = []

    if blocking_feedback_items > 0:
        warnings.append(
            f"{blocking_feedback_items} open blocking feedback item(s) must be "
            "resolved first."
        )

    if total_scores == 0:
        recommendations.append(
            "Run a Sales Workflow and let Quality Scoring evaluate at least one "
            "draft/workflow before assessing beta readiness."
        )
        return "not_ready", recommendations, warnings

    if average_quality_score is None:
        return "not_ready", recommendations, warnings

    if blocking_feedback_items > 0:
        recommendations.append("Resolve or reject every open blocking feedback item.")
        return "not_ready", recommendations, warnings

    if average_quality_score < 50:
        recommendations.append(
            "Average quality score is low — review weaknesses and improve "
            "prompts/profiles before testing further."
        )
        return "not_ready", recommendations, warnings

    if average_quality_score < settings.quality_min_workflow_score:
        recommendations.append(
            "Average quality score is below the configured minimum "
            f"({settings.quality_min_workflow_score}) — keep iterating."
        )
        return "needs_improvement", recommendations, warnings

    if (
        settings.quality_require_human_feedback_for_beta
        and total_feedback_items == 0
    ):
        recommendations.append(
            "No human feedback has been recorded yet — QUALITY_REQUIRE_HUMAN_"
            "FEEDBACK_FOR_BETA is enabled, so at least one reviewed feedback "
            "item is expected before calling this beta_ready."
        )
        return "beta_testable", recommendations, warnings

    recommendations.append(
        "Read CUSTOMER_READINESS.md — beta_ready is a technical signal only, "
        "not a legal or contractual clearance."
    )
    return "beta_ready", recommendations, warnings
