from enum import Enum


class LeadStatus(str, Enum):
    """Lifecycle stages of a sales lead."""

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    WON = "won"
    LOST = "lost"


class LeadSource(str, Enum):
    """Channel a lead originated from."""

    WEBSITE = "website"
    REFERRAL = "referral"
    OUTBOUND = "outbound"
    EVENT = "event"
    OTHER = "other"


class InteractionType(str, Enum):
    """Kind of touchpoint recorded against a lead."""

    EMAIL = "email"
    CALL = "call"
    MEETING = "meeting"
    NOTE = "note"
