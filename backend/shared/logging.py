"""Structured, stdout-based logging setup for the whole application.

Container log drivers (Docker, most PaaS providers) capture stdout/stderr, so
a single stream handler with a consistent ``key=value`` format is enough —
there is no local log file to rotate or manage.
"""

from __future__ import annotations

import logging
import sys

from backend.shared.config import Settings

_SENSITIVE_KEYWORDS = ("api_key", "apikey", "password", "secret", "token", "authorization")


class _RedactingFilter(logging.Filter):
    """Redact any log record whose message mentions a sensitive keyword.

    This is a defense-in-depth backstop, not a substitute for simply never
    logging secrets in the first place — application code must not pass API
    keys, passwords, or tokens into log messages.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage().lower()
        if any(keyword in message for keyword in _SENSITIVE_KEYWORDS):
            record.msg = "[redacted log message: contained a sensitive keyword]"
            record.args = ()
        return True


def configure_logging(settings: Settings) -> None:
    """Configure the root logger. Call once at process startup.

    ``DEBUG=true`` raises verbosity to DEBUG and re-enables the normally
    quiet SQLAlchemy engine logger; otherwise the app logs at INFO and
    third-party libraries are kept at WARNING to avoid noise.
    """
    level = logging.DEBUG if settings.debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s level=%(levelname)s logger=%(name)s message=%(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )
    handler.addFilter(_RedactingFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )
    # uvicorn's own access logger already reports each request; keep it as-is
    # rather than duplicating request logs through the app logger.
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
