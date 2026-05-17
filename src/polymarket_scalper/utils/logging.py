from __future__ import annotations

import logging
from typing import Any


class KeyValueFormatter(logging.Formatter):
    """Small formatter that preserves readability without adding heavy dependencies."""

    def format(self, record: logging.LogRecord) -> str:
        base = (
            f"{self.formatTime(record, self.datefmt)} | {record.levelname} | "
            f"{record.name} | {record.getMessage()}"
        )
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key
            not in {
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
                "taskName",
            }
        }
        if extras:
            rendered = " ".join(f"{key}={value}" for key, value in sorted(extras.items()))
            return f"{base} | {rendered}"
        return base


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(KeyValueFormatter(datefmt="%Y-%m-%dT%H:%M:%S%z"))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_settings_summary(logger: logging.Logger, settings: Any) -> None:
    """Emit a safe, redacted settings summary for startup diagnostics."""

    logger.info("settings_loaded", extra={"settings": settings.redacted_summary()})
