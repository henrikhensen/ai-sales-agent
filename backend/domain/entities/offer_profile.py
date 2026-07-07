from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class OfferProfile:
    """A definition of what is being sold: value proposition, benefits,
    proof, and guardrails against overselling.

    ``forbidden_claims`` exists specifically to stop the LLM from making
    claims the seller hasn't actually verified — the Offer/Personalization/
    Email Draft services must actively avoid them, never merely display
    them as a suggestion.
    """

    name: str
    main_value_proposition: str
    description: str | None = None
    target_outcome: str | None = None
    pain_points_solved: list[str] = field(default_factory=list)
    key_benefits: list[str] = field(default_factory=list)
    differentiators: list[str] = field(default_factory=list)
    proof_points: list[str] = field(default_factory=list)
    case_study_notes: str | None = None
    pricing_notes: str | None = None
    call_to_action: str | None = None
    tone: str = "professional"
    language: str = "de"
    forbidden_claims: list[str] = field(default_factory=list)
    required_disclaimers: list[str] = field(default_factory=list)
    is_active: bool = True
    created_by_user_id: UUID | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
