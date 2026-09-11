"""Logging configuration for AI Financial Analyst Agent."""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = PROJECT_ROOT / "logs"


def setup_logger(
    name: str = "financial_analyst",
    log_dir: Path = DEFAULT_LOG_DIR,
    log_level: Optional[str] = None,
) -> logging.Logger:
    """Sets up a logger with console and file handlers.

    Args:
        name: Logger name.
        log_dir: Directory to save log files.
        log_level: Log level override (DEBUG, INFO, WARNING, ERROR). Defaults to LOG_LEVEL env var or INFO.

    Returns:
        Configured logging.Logger instance.
    """
    if log_level is None:
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    level = getattr(logging, log_level, logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Root logger captures everything; handlers filter

    # Prevent duplicate handlers if setup_logger is called repeatedly
    if logger.handlers:
        return logger

    log_dir.mkdir(parents=True, exist_ok=True)
    today_str = datetime.now().strftime("%Y%m%d")
    log_file = log_dir / f"financial_analyst_{today_str}.log"

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler (must use stderr to prevent breaking MCP JSON-RPC protocol on stdout)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (captures DEBUG and above)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
