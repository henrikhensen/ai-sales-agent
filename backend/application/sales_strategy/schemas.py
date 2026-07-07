"""Schemas for ICP (Ideal Customer Profile) and Offer profiles.

Used both by the ICP/Offer services directly and as ``response_model`` for
``backend/api/v1/routes/sales_strategy.py``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

FitLevel = Literal["excellent", "good", "medium", "weak", "not_fit"]


# -- ICP ------------------------------------------------------------------------


class ICPProfileResponse(BaseModel):
    """A single ICP profile. Used only to score existing data against —
    never to scrape or fetch new external data."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    target_industries: list[str]
    excluded_industries: list[str]
    target_company_sizes: list[str]
    target_locations: list[str]
    target_languages: list[str]
    target_keywords: list[str]
    negative_keywords: list[str]
    target_pain_points: list[str]
    buying_triggers: list[str]
    required_signals: list[str]
    excluded_signals: list[str]
    buyer_personas: list[str]
    preferred_titles: list[str]
    excluded_titles: list[str]
    minimum_fit_score: int
    scoring_weights: dict[str, Any] | None
    is_active: bool
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class CreateICPProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    target_industries: list[str] = Field(default_factory=list)
    excluded_industries: list[str] = Field(default_factory=list)
    target_company_sizes: list[str] = Field(default_factory=list)
    target_locations: list[str] = Field(default_factory=list)
    target_languages: list[str] = Field(default_factory=list)
    target_keywords: list[str] = Field(default_factory=list)
    negative_keywords: list[str] = Field(default_factory=list)
    target_pain_points: list[str] = Field(default_factory=list)
    buying_triggers: list[str] = Field(default_factory=list)
    required_signals: list[str] = Field(default_factory=list)
    excluded_signals: list[str] = Field(default_factory=list)
    buyer_personas: list[str] = Field(default_factory=list)
    preferred_titles: list[str] = Field(default_factory=list)
    excluded_titles: list[str] = Field(default_factory=list)
    minimum_fit_score: int = Field(default=70, ge=0, le=100)
    scoring_weights: dict[str, Any] | None = None
    is_active: bool = True


class UpdateICPProfileRequest(BaseModel):
    """Only fields present in the request body are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    target_industries: list[str] | None = None
    excluded_industries: list[str] | None = None
    target_company_sizes: list[str] | None = None
    target_locations: list[str] | None = None
    target_languages: list[str] | None = None
    target_keywords: list[str] | None = None
    negative_keywords: list[str] | None = None
    target_pain_points: list[str] | None = None
    buying_triggers: list[str] | None = None
    required_signals: list[str] | None = None
    excluded_signals: list[str] | None = None
    buyer_personas: list[str] | None = None
    preferred_titles: list[str] | None = None
    excluded_titles: list[str] | None = None
    minimum_fit_score: int | None = Field(default=None, ge=0, le=100)
    scoring_weights: dict[str, Any] | None = None
    is_active: bool | None = None


class ICPProfileListResponse(BaseModel):
    items: list[ICPProfileResponse]
    limit: int
    offset: int


class ICPFitCheckRequest(BaseModel):
    """Ad-hoc scoring input — manually entered data or already-fetched
    website research text. Never triggers a new external fetch/scrape."""

    icp_profile_id: UUID
    company_name: str | None = Field(default=None, max_length=200)
    industry: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    company_size: str | None = Field(default=None, max_length=100)
    website_text: str | None = Field(default=None, max_length=20000)
    notes: str | None = Field(default=None, max_length=5000)
    keywords: list[str] = Field(default_factory=list)


class ICPFitCheckResponse(BaseModel):
    icp_profile_id: UUID
    fit_score: int
    fit_level: FitLevel
    matched_signals: list[str]
    missing_signals: list[str]
    negative_signals: list[str]
    recommendation: str
    warnings: list[str]


# -- Offer ------------------------------------------------------------------------


class OfferProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    main_value_proposition: str
    description: str | None
    target_outcome: str | None
    pain_points_solved: list[str]
    key_benefits: list[str]
    differentiators: list[str]
    proof_points: list[str]
    case_study_notes: str | None
    pricing_notes: str | None
    call_to_action: str | None
    tone: str
    language: str
    forbidden_claims: list[str]
    required_disclaimers: list[str]
    is_active: bool
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class CreateOfferProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    main_value_proposition: str = Field(min_length=1, max_length=2000)
    description: str | None = Field(default=None, max_length=5000)
    target_outcome: str | None = Field(default=None, max_length=1000)
    pain_points_solved: list[str] = Field(default_factory=list)
    key_benefits: list[str] = Field(default_factory=list)
    differentiators: list[str] = Field(default_factory=list)
    proof_points: list[str] = Field(default_factory=list)
    case_study_notes: str | None = Field(default=None, max_length=5000)
    pricing_notes: str | None = Field(default=None, max_length=2000)
    call_to_action: str | None = Field(default=None, max_length=500)
    tone: str = Field(default="professional", max_length=50)
    language: str = Field(default="de", max_length=50)
    forbidden_claims: list[str] = Field(default_factory=list)
    required_disclaimers: list[str] = Field(default_factory=list)
    is_active: bool = True


class UpdateOfferProfileRequest(BaseModel):
    """Only fields present in the request body are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    main_value_proposition: str | None = Field(default=None, min_length=1, max_length=2000)
    description: str | None = Field(default=None, max_length=5000)
    target_outcome: str | None = Field(default=None, max_length=1000)
    pain_points_solved: list[str] | None = None
    key_benefits: list[str] | None = None
    differentiators: list[str] | None = None
    proof_points: list[str] | None = None
    case_study_notes: str | None = Field(default=None, max_length=5000)
    pricing_notes: str | None = Field(default=None, max_length=2000)
    call_to_action: str | None = Field(default=None, max_length=500)
    tone: str | None = Field(default=None, max_length=50)
    language: str | None = Field(default=None, max_length=50)
    forbidden_claims: list[str] | None = None
    required_disclaimers: list[str] | None = None
    is_active: bool | None = None


class OfferProfileListResponse(BaseModel):
    items: list[OfferProfileResponse]
    limit: int
    offset: int


class OfferPreviewRequest(BaseModel):
    offer_profile_id: UUID


class OfferPreviewResponse(BaseModel):
    offer_profile_id: UUID
    summary: str
    positioning: str
    suggested_cta: str | None
    warnings: list[str]
