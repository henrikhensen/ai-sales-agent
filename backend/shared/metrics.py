"""In-memory, process-local metrics.

Deliberately simple counters instead of a Prometheus integration — this
project's scope doesn't warrant that dependency. Metrics reset whenever the
process restarts; that's an accepted trade-off for a single-instance
deployment. Never records personal data, email/reply content, prompts, or
secrets — only counts and aggregate timings.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RequestMetrics:
    request_count: int = 0
    # Any response with status_code >= 400 (client or server error).
    request_error_count: int = 0
    total_duration_ms: float = 0.0


@dataclass
class Counters:
    llm_test_count: int = 0
    do_not_contact_block_count: int = 0


_requests = RequestMetrics()
_counters = Counters()


def record_request(status_code: int, duration_ms: float) -> None:
    _requests.request_count += 1
    if status_code >= 400:
        _requests.request_error_count += 1
    _requests.total_duration_ms += duration_ms


def increment_llm_test_count() -> None:
    _counters.llm_test_count += 1


def increment_do_not_contact_block_count() -> None:
    _counters.do_not_contact_block_count += 1


def get_request_metrics() -> RequestMetrics:
    return _requests


def get_counters() -> Counters:
    return _counters


def reset_metrics() -> None:
    """Reset all in-memory counters. Used by tests to avoid cross-test
    interference; safe to call in production (e.g. after a scheduled
    metrics export) since nothing here is durable anyway."""
    global _requests, _counters
    _requests = RequestMetrics()
    _counters = Counters()
