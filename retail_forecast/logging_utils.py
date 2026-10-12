"""Project logging helpers."""

from __future__ import annotations

import logging
from pathlib import Path

from retail_forecast.config import PROJECT_ROOT


def setup_logger(name: str, log_file: str | None = None) -> logging.Logger:
    """Create a logger that writes to console and, optionally, a file."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if log_file:
        path = PROJECT_ROOT / "logs" / log_file
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger
