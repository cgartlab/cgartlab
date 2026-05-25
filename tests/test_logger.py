from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import pytest

from rss_updater.logger import setup_logging


@pytest.fixture(autouse=True)
def _reset_logger():
    logger = logging.getLogger("rss_updater")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    yield
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)


class TestJsonFormatter:
    def test_json_formatter_with_exception(self):
        from rss_updater.logger import _JsonFormatter

        formatter = _JsonFormatter()
        record = logging.LogRecord(
            name="rss_updater",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="error occurred",
            args=(),
            exc_info=None,
        )
        record.exc_info = (Exception, Exception("test exc"), None)
        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert data["message"] == "error occurred"
        assert "exception" in data


class TestSetupLogging:
    def test_info_level_logged(self, caplog):
        tmpdir = tempfile.mkdtemp()
        try:
            setup_logging(Path(tmpdir), level="INFO")
            logger = logging.getLogger("rss_updater")
            with caplog.at_level(logging.INFO, logger="rss_updater"):
                logger.info("test info message")
            assert "test info message" in caplog.text
            assert "INFO" in caplog.text
        finally:
            for handler in logging.getLogger("rss_updater").handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_json_format_file_output(self):
        tmpdir = tempfile.mkdtemp()
        try:
            log_dir = Path(tmpdir)
            setup_logging(log_dir, level="INFO", json_format=True)
            logger = logging.getLogger("rss_updater")
            logger.info("json test message")

            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.flush()
                    handler.close()

            log_file = log_dir / "rss_updater.log"
            content = log_file.read_text(encoding="utf-8").strip()
            assert content
            record = json.loads(content)
            assert record["level"] == "INFO"
            assert record["message"] == "json test message"
            assert "timestamp" in record
            assert "name" in record
        finally:
            for handler in logging.getLogger("rss_updater").handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_plain_format_file_output(self):
        tmpdir = tempfile.mkdtemp()
        try:
            log_dir = Path(tmpdir)
            setup_logging(log_dir, level="INFO", json_format=False)
            logger = logging.getLogger("rss_updater")
            logger.info("plain test message")

            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.flush()
                    handler.close()

            log_file = log_dir / "rss_updater.log"
            content = log_file.read_text(encoding="utf-8").strip()
            assert "plain test message" in content
            assert "rss_updater" in content
        finally:
            for handler in logging.getLogger("rss_updater").handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_setup_logging_clears_existing_handlers(self):
        logger = logging.getLogger("rss_updater")
        logger.addHandler(logging.StreamHandler())
        assert len(logger.handlers) > 0
        tmpdir = tempfile.mkdtemp()
        try:
            setup_logging(Path(tmpdir), level="INFO")
            assert len(logger.handlers) == 2
        finally:
            for handler in logging.getLogger("rss_updater").handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)
