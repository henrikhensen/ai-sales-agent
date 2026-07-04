"""Prompt design for the Personalization Engine.

The system prompt encodes the hard compliance rules (no fabrication, no
outreach, no aggressive sales language, JSON-only). The builder renders the
user-supplied facts into a task prompt without adding any information of its
own.
"""

from __future__ import annotations

from backend.agents.personalization.schemas import PersonalizationRequest

PERSONALIZATION_SYSTEM_PROMPT = (
    "You are a Personalization Engine for a B2B sales team. Your job is to turn "
    "company, lead and analysis context into a structured personalization "
    "strategy for a human seller, using ONLY the information the user provides.\n"
    "\n"
    "You MUST follow these rules without exception:\n"
    "1. Return ONLY a single valid JSON object that conforms exactly to the "
    "requested output schema. No prose, no markdown, no code fences.\n"
    "2. Do NOT invent facts. Never fabricate contact persons, names, email "
    "addresses, phone numbers, revenue figures, employee counts, funding, or "
    "customer references.\n"
    "3. Use ONLY the information contained in the user input (including any "
    "lead research or company intelligence summaries provided). Do not rely on "
    "unverifiable assumptions or private / unlawfully obtained data.\n"
    "4. 'relevant_observations' and 'possible_conversation_starters' may only "
    "contain facts or angles that are grounded in the input. Never fabricate a "
    "detail to make a starter sound more personal.\n"
    "5. 'do_not_use_claims' must list any claim that would strengthen the pitch "
    "but is NOT sufficiently backed by the input, so the seller knows not to "
    "use it.\n"
    "6. If information is missing, do not guess — list what is missing in the "
    "'missing_information' field.\n"
    "7. When something is uncertain or inferred, lower the 'confidence_score' "
    "accordingly. A strategy built on little input must have a low score.\n"
    "8. State the basis of your analysis in 'sources_used' (for example "
    "'user-provided lead summary', 'company intelligence summary'). Do not "
    "claim sources you were not given.\n"
    "9. 'suggested_ctas' must contain only short call-to-action ideas (e.g. "
    "'propose a 15-minute discovery call'). NEVER write a ready-to-send email, "
    "message, or outreach script.\n"
    "10. Do not use aggressive, pushy, or spammy sales language anywhere in the "
    "output.\n"
    "11. Perform personalization strategy work ONLY. Never draft, schedule, or "
    "send any outreach, email, message, or call, and never claim to have "
    "contacted anyone. A human decides on any contact.\n"
    "\n"
    "The confidence_score is a float between 0.0 and 1.0."
)


def build_personalization_prompt(request: PersonalizationRequest) -> str:
    """Render the task prompt from a validated request.

    Optional fields that were not supplied are marked as ``not provided`` so
    the model is explicitly told which facts are missing rather than being
    left to fill the gap itself.
    """

    def _line(label: str, value: object) -> str:
        if value is None:
            return f"- {label}: not provided"
        if isinstance(value, list):
            return f"- {label}: {', '.join(value) if value else 'not provided'}"
        return f"- {label}: {value}"

    return (
        "Build a personalization strategy for the following sales context, "
        "using ONLY the details below. Anything not stated here is unknown and "
        "belongs in 'missing_information'.\n"
        "\n"
        "Sales context:\n"
        f"{_line('Company name', request.company_name)}\n"
        f"{_line('Website URL', request.website_url)}\n"
        f"{_line('Industry', request.industry)}\n"
        f"{_line('Location', request.location)}\n"
        f"{_line('Lead research summary', request.lead_summary)}\n"
        f"{_line('Company intelligence summary', request.company_intelligence_summary)}\n"
        f"{_line('Target persona', request.target_persona)}\n"
        f"{_line('Product or service offered', request.product_or_service_offered)}\n"
        f"{_line('Value proposition', request.value_proposition)}\n"
        f"{_line('Known pain points', request.known_pain_points)}\n"
        f"{_line('Known triggers', request.known_triggers)}\n"
        f"{_line('Notes', request.notes)}\n"
        "\n"
        "Return the personalization strategy as a single JSON object matching "
        "the schema. Do not write an email or any ready-to-send message."
    )
