from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from rss_updater.history import HistoryManager
from rss_updater.models import CheckResult


@pytest.fixture
def tmp_history_dir(tmp_path: Path) -> Path:
    return tmp_path / "history"


class TestHistoryManagerBasic:
    def test_load_empty_history(self, tmp_history_dir: Path):
        mgr = HistoryManager(tmp_history_dir)
        assert mgr.load_history() == {}

    def test_set_and_get_content_hash(self, tmp_history_dir: Path):
        mgr = HistoryManager(tmp_history_dir)
        mgr.set_last_content_hash("feed_a", "hash123")
        assert mgr.get_last_content_hash("feed_a") == "hash123"
        assert mgr.get_last_content_hash("feed_b") is None

    def test_add_check_result(self, tmp_history_dir: Path):
        mgr = HistoryManager(tmp_history_dir)
        result = CheckResult(
            status="success",
            timestamp=datetime.now(UTC).isoformat(),
            feed_name="feed_a",
            articles_count=5,
            new_articles=[],
            content_hash="abc",
        )
        mgr.add_check_result(result)
        checks = mgr.get_recent_checks("feed_a")
        assert len(checks) == 1
        assert checks[0]["status"] == "success"
        assert checks[0]["content_hash"] == "abc"

    def test_get_recent_checks_limit(self, tmp_history_dir: Path):
        mgr = HistoryManager(tmp_history_dir)
        base = datetime.now(UTC)
        for i in range(15):
            result = CheckResult(
                status="success",
                timestamp=(base - timedelta(minutes=i)).isoformat(),
                feed_name="feed_a",
                articles_count=1,
                new_articles=[],
            )
            mgr.add_check_result(result)
        checks = mgr.get_recent_checks("feed_a", limit=5)
        assert len(checks) == 5

    def test_persistence(self, tmp_history_dir: Path):
        mgr = HistoryManager(tmp_history_dir)
        mgr.set_last_content_hash("feed_x", "hash_xyz")
        mgr2 = HistoryManager(tmp_history_dir)
        assert mgr2.get_last_content_hash("feed_x") == "hash_xyz"


class TestHistoryManagerConcurrency:
    def test_concurrent_writes_no_corruption(self, tmp_history_dir: Path):
        mgr = HistoryManager(tmp_history_dir)
        errors: list[Exception] = []
        threads: list[threading.Thread] = []
        barrier = threading.Barrier(20)

        def writer(feed: str, idx: int) -> None:
            try:
                barrier.wait(timeout=5)
                result = CheckResult(
                    status="success",
                    timestamp=(datetime.now(UTC) + timedelta(milliseconds=idx)).isoformat(),
                    feed_name=feed,
                    articles_count=idx,
                    new_articles=[],
                )
                mgr.add_check_result(result)
            except Exception as exc:
                errors.append(exc)

        for i in range(20):
            t = threading.Thread(target=writer, args=("feed_concurrent", i))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert not errors
        checks = mgr.get_recent_checks("feed_concurrent", limit=100)
        assert len(checks) == 20


class TestHistoryManagerEdgeCases:
    def test_load_history_corrupted_json(self, tmp_history_dir: Path):
        mgr = HistoryManager(tmp_history_dir)
        mgr.history_file.write_text("not json", encoding="utf-8")
        result = mgr.load_history()
        assert result == {}

    def test_load_history_empty_file(self, tmp_history_dir: Path):
        mgr = HistoryManager(tmp_history_dir)
        mgr.history_file.write_text("", encoding="utf-8")
        result = mgr.load_history()
        assert result == {}

    def test_save_history_exception_cleanup(self, tmp_history_dir: Path):
        mgr = HistoryManager(tmp_history_dir)
        history = {"feed": {"last_content_hash": "abc"}}
        with (
            patch("rss_updater.history.os.replace", side_effect=OSError("disk full")),
            patch("rss_updater.history.os.unlink") as mock_unlink,
            pytest.raises(OSError),
        ):
            mgr.save_history(history)
        assert mock_unlink.call_count >= 1

    def test_parse_timestamp_invalid(self, tmp_history_dir: Path):
        mgr = HistoryManager(tmp_history_dir)
        result = mgr._parse_timestamp("invalid-timestamp")
        assert result == datetime.min.replace(tzinfo=UTC)


class TestHistoryManagerCleanup:
    def test_cleanup_old_checks(self, tmp_history_dir: Path):
        mgr = HistoryManager(tmp_history_dir)
        now = datetime.now(UTC)
        old = now - timedelta(days=31)
        recent = now - timedelta(days=1)

        old_result = CheckResult(
            status="success",
            timestamp=old.isoformat(),
            feed_name="feed_cleanup",
            articles_count=1,
            new_articles=[],
        )
        recent_result = CheckResult(
            status="success",
            timestamp=recent.isoformat(),
            feed_name="feed_cleanup",
            articles_count=2,
            new_articles=[],
        )
        mgr.add_check_result(old_result)
        mgr.add_check_result(recent_result)

        checks = mgr.get_recent_checks("feed_cleanup", limit=100)
        assert len(checks) == 1
        assert checks[0]["articles_count"] == 2

    def test_cleanup_removes_empty_feed(self, tmp_history_dir: Path):
        mgr = HistoryManager(tmp_history_dir)
        now = datetime.now(UTC)
        old = now - timedelta(days=31)

        old_result = CheckResult(
            status="success",
            timestamp=old.isoformat(),
            feed_name="feed_empty",
            articles_count=1,
            new_articles=[],
        )
        mgr.add_check_result(old_result)
        history = mgr.load_history()
        assert "feed_empty" not in history
