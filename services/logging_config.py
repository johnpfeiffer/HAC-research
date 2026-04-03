"""Centralized logging configuration for the application."""

import logging
import os
import sys


def setup_logging(level: str | None = None) -> None:
    """Configure root logger with a consistent format.

    Args:
        level: Override log level (e.g. "DEBUG", "INFO"). Falls back to
               LOG_LEVEL env var, then defaults to INFO.
    """
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level, logging.INFO))

    # Avoid duplicate handlers on repeated calls (e.g. Streamlit reruns)
    if not root.handlers:
        root.addHandler(handler)

    # Quieten noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "openai", "langchain", "langsmith"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
