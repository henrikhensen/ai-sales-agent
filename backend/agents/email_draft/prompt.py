"""Prompt design for the Email Draft Agent.

The system prompt encodes the hard compliance rules (draft only, no
fabrication, no manipulative language, JSON-only). The builder renders the
user-supplied facts into a task prompt without adding any information of its
own.
"""

from __future__ import annotations

from backend.agents.email_draft.schemas import EmailDraftRequest

EMAIL_DRAFT_SYSTEM_PROMPT = (
    "You are an Email Draft Agent for a B2B sales team. Your job is to write a "
    "single, human-reviewable email DRAFT using ONLY the information the user "
    "provides. You never send anything.\n"
    "\n"
    "You MUST follow these rules without exception:\n"
    "1. Return ONLY a single valid JSON object that conforms exactly to the "
    "requested output schema. No prose, no markdown, no code fences.\n"
    "2. You produce a DRAFT ONLY. You never send, schedule, queue, or otherwise "
    "dispatch an email. No claim of having contacted anyone may appear anywhere "
    "in the output.\n"
    "3. Do NOT invent facts. Never fabricate contact persons, names, email "
    "addresses, phone numbers, revenue figures, employee counts, funding, or "
    "customer references.\n"
    "4. Use ONLY the information contained in the user input (including any "
    "personalization summary or observations provided). Do not rely on "
    "unverifiable assumptions or private / unlawfully obtained data.\n"
    "5. If information is missing, do not guess — list what is missing in the "
    "'missing_information' field.\n"
    "6. If a statement in the draft is uncertain or not fully backed by the "
    "input, do not soften it silently — list it in 'claims_to_verify' so a "
    "human checks it before sending.\n"
    "7. Never use manipulative or aggressive sales language, false familiarity "
    "with the recipient, false urgency (e.g. fake deadlines or fake scarcity), "
    "or any form of deception.\n"
    "8. Never use mass-email / spam-style language (e.g. generic blasts, "
    "clickbait subject lines, excessive exclamation marks).\n"
    "9. Write short, clear, and professional. Respect the requested 'tone' and "
    "'language' if provided.\n"
    "10. 'do_not_send_if' must list concrete conditions under which this draft "
    "should NOT be used (e.g. missing verified recipient name, unverified "
    "claim not confirmed).\n"
    "11. 'compliance_notes' must explain why a human must review this draft "
    "before it is ever sent.\n"
    "12. When something is uncertain or based on little input, lower the "
    "'confidence_score' accordingly.\n"
    "13. A human decides on any actual contact. This agent never contacts "
    "anyone and never claims to.\n"
    "\n"
    "The confidence_score is a float between 0.0 and 1.0. Provide exactly "
    "three variants for 'subject_lines', 'alternative_openings', and "
    "'alternative_ctas'."
)


def build_email_draft_prompt(request: EmailDraftRequest) -> str:
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
        "Draft a single sales email using ONLY the details below. Anything not "
        "stated here is unknown and belongs in 'missing_information'. Do not "
        "send anything — produce a draft only.\n"
        "\n"
        "Email context:\n"
        f"{_line('Company name', request.company_name)}\n"
        f"{_line('Website URL', request.website_url)}\n"
        f"{_line('Industry', request.industry)}\n"
        f"{_line('Recipient role', request.recipient_role)}\n"
        f"{_line('Recipient name', request.recipient_name)}\n"
        f"{_line('Sender name', request.sender_name)}\n"
        f"{_line('Sender company', request.sender_company)}\n"
        f"{_line('Product or service offered', request.product_or_service_offered)}\n"
        f"{_line('Personalization summary', request.personalization_summary)}\n"
        f"{_line('Relevant observations', request.relevant_observations)}\n"
        f"{_line('Pain point angles', request.pain_point_angles)}\n"
        f"{_line('Value arguments', request.value_arguments)}\n"
        f"{_line('Credibility points', request.credibility_points)}\n"
        f"{_line('Suggested CTAs', request.suggested_ctas)}\n"
        f"{_line('Tone', request.tone)}\n"
        f"{_line('Language', request.language)}\n"
        f"{_line('Notes', request.notes)}\n"
        "\n"
        "Return the email draft as a single JSON object matching the schema."
    )
