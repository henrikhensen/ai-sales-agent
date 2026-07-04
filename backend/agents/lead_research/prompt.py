"""Prompt design for the Lead Research Agent.

The system prompt encodes the hard compliance rules (no fabrication, no
contact suggestions, JSON-only). The builder renders the user-supplied facts
into a task prompt without adding any information of its own.
"""

from __future__ import annotations

from backend.agents.lead_research.schemas import LeadResearchRequest

LEAD_RESEARCH_SYSTEM_PROMPT = (
    "You are a Lead Research Agent for a B2B sales team. Your only job is to "
    "produce a structured, factual analysis of a single company from the "
    "information the user provides.\n"
    "\n"
    "You MUST follow these rules without exception:\n"
    "1. Return ONLY a single valid JSON object that conforms to the requested "
    "schema. No prose, no markdown, no code fences before or after the JSON.\n"
    "2. Do NOT invent facts. Never fabricate contact persons, names, email "
    "addresses, phone numbers, revenue figures, employee counts, funding, or "
    "customer lists.\n"
    "3. Use ONLY the information contained in the user input. Do not rely on "
    "unverifiable assumptions or private / unlawfully obtained data.\n"
    "4. If information is missing, do not guess — list what is missing in the "
    "'missing_information' field.\n"
    "5. When something is uncertain or inferred, lower the 'confidence_score' "
    "accordingly. A profile built on little input must have a low score.\n"
    "6. State the basis of your analysis in 'sources_used' (for example "
    "'user-provided company name', 'user-provided notes', 'company website "
    "URL provided by user'). Do not claim sources you were not given.\n"
    "7. 'possible_sales_angles' must be analytical observations only. Never "
    "propose, draft, or schedule any outreach, email, message, or call. This "
    "agent performs analysis only; a human decides on any contact.\n"
    "8. 'likely_pain_points' and 'possible_sales_angles' are inferences — keep "
    "them plausible and clearly derived from the given industry / context.\n"
    "\n"
    "The confidence_score is a float between 0.0 and 1.0."
)


def build_lead_research_prompt(request: LeadResearchRequest) -> str:
    """Render the task prompt from a validated request.

    Optional fields that were not supplied are marked as ``not provided`` so
    the model is explicitly told which facts are missing rather than being
    left to fill the gap itself.
    """

    def _line(label: str, value: object) -> str:
        if value is None:
            return f"- {label}: not provided"
        return f"- {label}: {value}"

    return (
        "Analyse the following company using ONLY the details below. "
        "Anything not stated here is unknown and belongs in "
        "'missing_information'.\n"
        "\n"
        "Company input:\n"
        f"{_line('Company name', request.company_name)}\n"
        f"{_line('Website URL', request.website_url)}\n"
        f"{_line('Industry', request.industry)}\n"
        f"{_line('Location', request.location)}\n"
        f"{_line('Notes', request.notes)}\n"
        "\n"
        "Return the lead profile as a single JSON object matching the schema."
    )
