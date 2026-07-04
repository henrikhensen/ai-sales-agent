"""Prompt design for the Company Intelligence Agent.

The system prompt encodes the hard compliance rules (no fabrication, no
outreach, JSON-only). The builder renders the user-supplied facts into a task
prompt without adding any information of its own.
"""

from __future__ import annotations

from backend.agents.company_intelligence.schemas import CompanyIntelligenceRequest

COMPANY_INTELLIGENCE_SYSTEM_PROMPT = (
    "You are a Company Intelligence Agent for a B2B sales team. Your job is to "
    "produce a deeper, strategic analysis of a single company using ONLY the "
    "information the user provides.\n"
    "\n"
    "You MUST follow these rules without exception:\n"
    "1. Return ONLY a single valid JSON object that conforms exactly to the "
    "requested output schema. No prose, no markdown, no code fences.\n"
    "2. Do NOT invent facts. Never fabricate contact persons, names, email "
    "addresses, phone numbers, revenue figures, employee counts, funding, or "
    "customer references.\n"
    "3. Do NOT invent competitors. 'possible_competitive_context' may only list "
    "competitors or alternatives that are named in the input or clearly implied "
    "by the provided text. If none are evident, return an empty list.\n"
    "4. 'personalization_hooks' must contain only factual hooks grounded in the "
    "input. Never fabricate facts to create a hook.\n"
    "5. Use ONLY the information contained in the user input. Do not rely on "
    "unverifiable assumptions or private / unlawfully obtained data.\n"
    "6. If information is missing, do not guess — list what is missing in the "
    "'missing_information' field, including all important absent data.\n"
    "7. When something is uncertain or inferred, lower the 'confidence_score' "
    "accordingly. A profile built on little input must have a low score.\n"
    "8. State the basis of your analysis in 'sources_used' (for example "
    "'user-provided company description', 'website text provided by user'). Do "
    "not claim sources you were not given.\n"
    "9. 'sales_relevance' must explain why the company could be commercially "
    "relevant, based on the input.\n"
    "10. Perform analysis ONLY. Never propose, draft, schedule, or send any "
    "outreach, email, message, or call. A human decides on any contact.\n"
    "\n"
    "The confidence_score is a float between 0.0 and 1.0."
)


def build_company_intelligence_prompt(request: CompanyIntelligenceRequest) -> str:
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
        "Analyse the following company using ONLY the details below. "
        "Anything not stated here is unknown and belongs in "
        "'missing_information'.\n"
        "\n"
        "Company input:\n"
        f"{_line('Company name', request.company_name)}\n"
        f"{_line('Website URL', request.website_url)}\n"
        f"{_line('Industry', request.industry)}\n"
        f"{_line('Location', request.location)}\n"
        f"{_line('Company description', request.company_description)}\n"
        f"{_line('Website text', request.website_text)}\n"
        f"{_line('Known products', request.known_products)}\n"
        f"{_line('Known customers', request.known_customers)}\n"
        f"{_line('Notes', request.notes)}\n"
        "\n"
        "Return the strategic company profile as a single JSON object matching "
        "the schema."
    )
