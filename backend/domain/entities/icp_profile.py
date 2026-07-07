from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass
class ICPProfile:
    """An Ideal Customer Profile: describes the kind of company/lead the
    agent should prioritize, and the kind it should avoid.

    Used only to score existing data (manually entered, or already-fetched
    website research text) against these criteria — never to scrape or
    fetch new external data by itself. Scoring never invents facts; missing
    data always surfaces as a warning instead of being assumed.
    """

    name: str
    description: str | None = None
    target_industries: list[str] = field(default_factory=list)
    excluded_industries: list[str] = field(default_factory=list)
    target_company_sizes: list[str] = field(default_factory=list)
    target_locations: list[str] = field(default_factory=list)
    target_languages: list[str] = field(default_factory=list)
    target_keywords: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)
    target_pain_points: list[str] = field(default_factory=list)
    buying_triggers: list[str] = field(default_factory=list)
    required_signals: list[str] = field(default_factory=list)
    excluded_signals: list[str] = field(default_factory=list)
    buyer_personas: list[str] = field(default_factory=list)
    preferred_titles: list[str] = field(default_factory=list)
    excluded_titles: list[str] = field(default_factory=list)
    minimum_fit_score: int = 70
    scoring_weights: dict[str, Any] | None = None
    is_active: bool = True
    created_by_user_id: UUID | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
