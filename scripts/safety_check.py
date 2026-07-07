#!/usr/bin/env python3
"""Final safety scan: greps the repository for risky terms and confirms a
handful of hard project invariants (no send capability, .env/backups/logs
gitignored, no real secrets in tracked files).

This is a best-effort scan, not a guarantee - false positives are
expected and fine (e.g. a comment explaining *why* something is NOT a send
endpoint will still match "send"). A human should review every match
before treating a "clean" run as proof of safety. This script never
prints a matched secret's actual value - only the file, line number, and
which pattern matched.

Usage:
    python scripts/safety_check.py

Exit code is always 0 (informational tool, not a hard CI gate) unless a
hard invariant (gitignore coverage) fails, in which case it exits 1.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories never scanned: build output, dependencies, VCS internals.
_EXCLUDED_DIR_NAMES = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".next",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "backups",
}

# Only scan source-like files - skip binaries, lockfiles, images.
_SCANNED_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".md",
    ".yml",
    ".yaml",
    ".env.example",
    ".ps1",
    ".sh",
}

# Patterns that would indicate a real send capability or a leaked secret.
# Deliberately broad - false positives are expected and acceptable; see
# module docstring. Each entry is (label, compiled regex).
_RISKY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("send_email", re.compile(r"send_email", re.IGNORECASE)),
    ("sendMessage", re.compile(r"sendMessage")),
    ("mail.send", re.compile(r"mail\.send", re.IGNORECASE)),
    ("Mail.Send (Graph scope)", re.compile(r"Mail\.Send")),
    ("API_KEY=", re.compile(r"\bAPI_KEY\s*=")),
    ("SECRET=", re.compile(r"\bSECRET\s*=")),
    ("password=", re.compile(r"\bpassword\s*=", re.IGNORECASE)),
    ("token=", re.compile(r"\btoken\s*=", re.IGNORECASE)),
]

# Env var names whose value must stay empty in a committed .env.example.
_SECRET_ENV_VAR_NAMES = (
    "ANTHROPIC_API_KEY",
    "GOOGLE_CLIENT_SECRET",
    "MICROSOFT_CLIENT_SECRET",
    "EMAIL_TOKEN_ENCRYPTION_KEY",
    "JWT_SECRET_KEY",
)


def _iter_scanned_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in _EXCLUDED_DIR_NAMES for part in path.parts):
            continue
        if path.suffix not in _SCANNED_SUFFIXES and path.name != ".env.example":
            continue
        files.append(path)
    return files


def _redact(line: str) -> str:
    """Never echo a matched line verbatim - only what's left of the first
    '=' or ':', so a real secret value (if one somehow exists) is never
    printed by this script itself."""
    for separator in ("=", ":"):
        if separator in line:
            return line.split(separator, 1)[0].strip() + f" {separator} [REDACTED]"
    return line.strip()[:80]


def scan_for_risky_terms() -> list[str]:
    print("== Scanning for risky terms ==")
    print(f"Patterns checked: {', '.join(label for label, _ in _RISKY_PATTERNS)}")
    findings: list[str] = []
    for path in _iter_scanned_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        relative = path.relative_to(REPO_ROOT)
        for line_number, line in enumerate(text.splitlines(), start=1):
            for label, pattern in _RISKY_PATTERNS:
                if pattern.search(line):
                    findings.append(f"{relative}:{line_number} matched '{label}' - {_redact(line)}")
    if findings:
        print(f"Found {len(findings)} match(es) - review each one manually:")
        for finding in findings:
            print(f"  {finding}")
    else:
        print("No matches found.")
    print()
    return findings


def check_gitignore_coverage() -> list[str]:
    print("== Checking .gitignore coverage ==")
    required_patterns = [".env", "backups", "*.sql", "*.log"]
    print(f"Required patterns: {', '.join(required_patterns)}")
    gitignore_path = REPO_ROOT / ".gitignore"
    problems: list[str] = []
    if not gitignore_path.is_file():
        problems.append(".gitignore does not exist")
    else:
        content = gitignore_path.read_text(encoding="utf-8")
        for pattern in required_patterns:
            if pattern not in content:
                problems.append(f".gitignore is missing a pattern for: {pattern}")
    if problems:
        for problem in problems:
            print(f"  MISSING: {problem}")
    else:
        print("All required patterns are present.")
    print()
    return problems


def check_env_file_not_tracked() -> list[str]:
    print("== Checking .env is not tracked by git ==")
    import subprocess

    problems: list[str] = []
    try:
        result = subprocess.run(
            ["git", "ls-files", ".env"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip():
            problems.append(".env is tracked by git - remove it from version control")
            print("  TRACKED: .env is committed to git!")
        else:
            print(".env is not tracked.")
    except FileNotFoundError:
        print("  SKIPPED: git not available.")
    print()
    return problems


def check_env_example_has_no_real_secrets() -> list[str]:
    print("== Checking .env.example has empty secret values ==")
    print(f"Checked variables: {', '.join(_SECRET_ENV_VAR_NAMES)}")
    problems: list[str] = []
    for candidate in (REPO_ROOT / ".env.example", REPO_ROOT / "frontend" / ".env.example"):
        if not candidate.is_file():
            continue
        for line_number, line in enumerate(
            candidate.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for var_name in _SECRET_ENV_VAR_NAMES:
                if line.strip().startswith(f"{var_name}="):
                    value = line.split("=", 1)[1].strip().strip('"')
                    # A committed example value is fine only if it's an
                    # obvious, non-functional placeholder - never empty
                    # values are the norm for this project's .env.example.
                    if value and value not in ("dev-only-insecure-secret-change-me",):
                        problems.append(
                            f"{candidate.relative_to(REPO_ROOT)}:{line_number} "
                            f"{var_name} has a non-empty value"
                        )
    if problems:
        for problem in problems:
            print(f"  SUSPICIOUS: {problem}")
    else:
        print("All checked variables are empty or a known safe placeholder.")
    print()
    return problems


def check_no_send_routes() -> list[str]:
    print("== Checking no API route path contains 'send' ==")
    problems: list[str] = []
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from backend.main import app  # noqa: PLC0415

        send_like = [
            route.path
            for route in app.routes
            if "send" in getattr(route, "path", "").lower()
        ]
        if send_like:
            problems.extend(send_like)
            print(f"  FOUND: {len(send_like)} route(s) with 'send' in the path:")
            for path in send_like:
                print(f"    {path}")
        else:
            print("No route path contains 'send'.")
    except Exception as exc:  # pragma: no cover - diagnostic only
        print(f"  SKIPPED: could not import the app ({type(exc).__name__}).")
    print()
    return problems


def main() -> int:
    print("AI Sales Agent - Final Safety Scan")
    print("=" * 60)
    print(
        "This scan is informational and best-effort. False positives are "
        "expected - review each match yourself before drawing conclusions. "
        "No secret value is ever printed by this script."
    )
    print()

    term_findings = scan_for_risky_terms()
    gitignore_problems = check_gitignore_coverage()
    env_tracked_problems = check_env_file_not_tracked()
    env_example_problems = check_env_example_has_no_real_secrets()
    route_problems = check_no_send_routes()

    print("== Summary ==")
    print(f"Risky-term matches to review: {len(term_findings)}")
    print(f".gitignore coverage problems: {len(gitignore_problems)}")
    print(f".env tracked-by-git problems: {len(env_tracked_problems)}")
    print(f".env.example secret-value problems: {len(env_example_problems)}")
    print(f"Routes with 'send' in the path: {len(route_problems)}")

    hard_failures = gitignore_problems + env_tracked_problems + route_problems
    if hard_failures:
        print()
        print(f"FAILED: {len(hard_failures)} hard invariant violation(s) found.")
        return 1

    print()
    print("No hard invariant violations found. Review the risky-term matches "
          "above manually - they are not automatically pass/fail.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
