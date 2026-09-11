"""Unit tests for utils/logging_config.py."""

import os
import logging
import pytest
from pathlib import Path
from utils.logging_config import setup_logger


class TestLoggingConfig:
    def test_setup_logger_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        logger_name = "test_custom_logger"
        logger = setup_logger(name=logger_name, log_dir=tmp_path)

        assert logger.name == logger_name
        assert tmp_path.exists()

        logger.debug("Debug level message test")
        logger.info("Info level message test")

        log_files = list(tmp_path.glob("*.log"))
        assert len(log_files) >= 1

        content = log_files[0].read_text(encoding="utf-8")
        assert "Debug level message test" in content
        assert "Info level message test" in content
