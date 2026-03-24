"""Structured error reporting and logging for Refraction.

No GUI dependencies -- the SwiftUI frontend handles display.
"""

import logging
import logging.handlers
import os
import traceback

LOG_PATH = os.path.expanduser("~/Library/Logs/refraction.log")

# Set up logging
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
_logger = logging.getLogger("refraction")
_logger.setLevel(logging.DEBUG)

if not _logger.handlers:
    try:
        _handler = logging.handlers.RotatingFileHandler(
            LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"
        )
    except Exception:
        _handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    _logger.addHandler(_handler)


def log_info(msg: str) -> None:
    _logger.info(msg)


def log_warning(msg: str) -> None:
    _logger.warning(msg)


def log_error(msg: str, exc: Exception = None) -> None:
    if exc is not None:
        tb = traceback.format_exc()
        _logger.error("%s\n%s", msg, tb)
    else:
        _logger.error(msg)


class ErrorReporter:
    """Collect and log errors.  No GUI -- call summary() for text output."""

    def __init__(self):
        self._errors: list[dict] = []
        self._warnings: list[str] = []

    def report(self, title: str, message: str, exc: Exception = None,
               level: str = "error") -> None:
        """Log and store an error."""
        log_error(f"{title}: {message}", exc=exc)
        self._errors.append({"title": title, "message": message, "level": level})

    def warning(self, message: str) -> None:
        log_warning(message)
        self._warnings.append(message)

    @property
    def has_errors(self) -> bool:
        return len(self._errors) > 0

    @property
    def errors(self) -> list[dict]:
        return list(self._errors)

    @property
    def warnings(self) -> list[str]:
        return list(self._warnings)

    def summary(self) -> str:
        lines = []
        for e in self._errors:
            lines.append(f"[{e['level'].upper()}] {e['title']}: {e['message']}")
        for w in self._warnings:
            lines.append(f"[WARNING] {w}")
        return "\n".join(lines)


# Module-level singleton
reporter = ErrorReporter()
