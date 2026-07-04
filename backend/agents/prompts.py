"""Prompt templates and helpers shared by agents.

Kept free of business logic — this holds reusable prompt scaffolding only.
"""

DEMO_AGENT_SYSTEM_PROMPT = (
    "You are a demonstration agent used to verify that the AI agent framework "
    "is wired up correctly. Respond to the user's message concisely. Do not "
    "perform any real sales, research, or scoring work."
)


def build_demo_prompt(message: str) -> str:
    """Build the demo agent's user prompt from an input message."""
    return f"Message: {message}"
