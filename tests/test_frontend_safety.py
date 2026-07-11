"""Standing frontend safety regression: no send-capable UI anywhere.

This project's frontend has no Jest/RTL (PROJECT_RULES.md: no
unnecessary new tools), so this is a source-level check across every
``.tsx`` file in ``app/`` and ``components/`` rather than a rendered-DOM
assertion. It must keep passing across every redesign.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND = REPO_ROOT / "frontend"


def _all_frontend_source_files():
    for directory in ("app", "components"):
        yield from (FRONTEND / directory).rglob("*.tsx")


def test_no_send_button_label_anywhere_in_frontend_source():
    """'Senden'/'Versenden' (capitalized, whole word) is the shape a real
    send button would take in this app's German UI. It must never appear
    outside of a code comment documenting that it is deliberately absent."""
    pattern = re.compile(r"\bSenden\b|\bVersenden\b")
    offending: list[str] = []
    for file in _all_frontend_source_files():
        for line in file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("*"):
                continue
            if pattern.search(line):
                offending.append(f"{file}: {line.strip()}")
    assert offending == []
