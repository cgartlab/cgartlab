from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from rss_updater.models import AppConfig, Article, CheckResult, FeedConfig, Settings
from rss_updater.updater import RSSUpdater


class TestRSSUpdater:
    def _make_config(self, feeds: list[FeedConfig] | None = None) -> AppConfig:
        if feeds is None:
            feeds = [
                FeedConfig(
                    name="TestFeed",
                    url="https://example.com/feed.xml",
                    section_marker="TEST_FEED",
                    max_posts=3,
                    enabled=True,
                )
            ]
        return AppConfig(feeds=feeds, settings=Settings(history_dir=".rss_history_test"))

    def _make_readme(self, tmp_path: Path, content: str = "# README\n") -> str:
        readme = tmp_path / "README.md"
        readme.write_text(content, encoding="utf-8")
        return str(readme)

    def test_init(self) -> None:
        config = self._make_config()
        updater = RSSUpdater(config, check_mode=True, force=True)
        assert updater.config == config
        assert updater.check_mode is True
        assert updater.force is True

    def test_update_readme_normal_flow(self, tmp_path: Path) -> None:
        config = self._make_config()
        readme_path = self._make_readme(tmp_path)
        articles = [Article(title="A", link="https://a.com", date="2024-01-01")]

        updater = RSSUpdater(config)
        with (
            patch.object(updater.fetcher, "fetch", return_value=articles),
            patch.object(updater.detector, "detect_changes", return_value=(True, articles, "hash1")),
            patch("rss_updater.updater.send_notifications") as mock_notify,
        ):
            updated, results = updater.update_readme(readme_path)

        assert updated is True
        assert len(results) == 1
        assert results[0].status == "success"
        mock_notify.assert_called_once()
        new_content = Path(readme_path).read_text(encoding="utf-8")
        assert "A" in new_content

    def test_check_mode_does_not_write(self, tmp_path: Path, capsys: Any) -> None:
        config = self._make_config()
        readme_path = self._make_readme(tmp_path, "# README\n")
        original_content = Path(readme_path).read_text(encoding="utf-8")
        articles = [Article(title="A", link="https://a.com", date="2024-01-01")]

        updater = RSSUpdater(config, check_mode=True)
        with (
            patch.object(updater.fetcher, "fetch", return_value=articles),
            patch.object(updater.detector, "detect_changes", return_value=(True, articles, "hash1")),
            patch("rss_updater.updater.send_notifications"),
        ):
            updated, results = updater.update_readme(readme_path)

        assert updated is True
        assert Path(readme_path).read_text(encoding="utf-8") == original_content
        captured = capsys.readouterr()
        assert "NEW_CONTENT_DETECTED=true" in captured.out

    def test_force_mode_skips_detection(self, tmp_path: Path) -> None:
        config = self._make_config()
        readme_path = self._make_readme(tmp_path)
        articles = [Article(title="A", link="https://a.com", date="2024-01-01")]

        updater = RSSUpdater(config, force=True)
        with (
            patch.object(updater.fetcher, "fetch", return_value=articles),
            patch("rss_updater.updater.send_notifications") as mock_notify,
        ):
            updated, results = updater.update_readme(readme_path)

        assert updated is True
        assert results[0].status == "success"
        assert results[0].new_articles == articles
        mock_notify.assert_called_once()

    def test_no_changes(self, tmp_path: Path, capsys: Any) -> None:
        config = self._make_config()
        readme_path = self._make_readme(tmp_path)
        articles = [Article(title="A", link="https://a.com", date="2024-01-01")]

        updater = RSSUpdater(config)
        with (
            patch.object(updater.fetcher, "fetch", return_value=articles),
            patch.object(updater.detector, "detect_changes", return_value=(False, [], "hash1")),
            patch("rss_updater.updater.send_notifications") as mock_notify,
        ):
            updated, results = updater.update_readme(readme_path)

        assert updated is False
        assert results[0].status == "no_change"
        mock_notify.assert_not_called()
        captured = capsys.readouterr()
        assert "NEW_CONTENT_DETECTED=false" in captured.out
        assert "CONTENT_UPDATED=false" in captured.out

    def test_fetch_error(self, tmp_path: Path) -> None:
        config = self._make_config()
        readme_path = self._make_readme(tmp_path)

        updater = RSSUpdater(config)
        with patch.object(updater.fetcher, "fetch", return_value=None):
            updated, results = updater.update_readme(readme_path)

        assert updated is False
        assert results[0].status == "error"
        assert results[0].error_message == "Failed to fetch feed"

    def test_disabled_feed_skipped(self, tmp_path: Path) -> None:
        config = self._make_config([
            FeedConfig(
                name="DisabledFeed",
                url="https://example.com/feed.xml",
                section_marker="DISABLED",
                enabled=False,
            )
        ])
        readme_path = self._make_readme(tmp_path)

        updater = RSSUpdater(config)
        with patch.object(updater.fetcher, "fetch") as mock_fetch:
            updated, results = updater.update_readme(readme_path)

        mock_fetch.assert_not_called()
        assert results == []
        assert updated is False

    def test_run_returns_0_on_success(self, tmp_path: Path) -> None:
        config = self._make_config()
        _readme_path = self._make_readme(tmp_path)
        articles = [Article(title="A", link="https://a.com", date="2024-01-01")]

        updater = RSSUpdater(config)
        with patch.object(updater, "update_readme", return_value=(True, [
            CheckResult(
                status="success", timestamp="2024-01-01T00:00:00+00:00",
                feed_name="TestFeed", articles_count=1, new_articles=articles,
            ),
        ])):
            assert updater.run() == 0

    def test_run_returns_1_on_error(self, tmp_path: Path) -> None:
        config = self._make_config()
        _readme_path = self._make_readme(tmp_path)

        updater = RSSUpdater(config)
        with patch.object(updater, "update_readme", return_value=(False, [
            CheckResult(
                status="error", timestamp="2024-01-01T00:00:00+00:00",
                feed_name="TestFeed", articles_count=0, new_articles=[], error_message="fail",
            ),
        ])):
            assert updater.run() == 1

    def test_atomic_write(self, tmp_path: Path) -> None:
        target = tmp_path / "output.md"
        RSSUpdater._atomic_write(target, "hello world")
        assert target.read_text(encoding="utf-8") == "hello world"

    def test_readme_not_found(self) -> None:
        config = self._make_config()
        updater = RSSUpdater(config)
        updated, results = updater.update_readme("nonexistent.md")
        assert updated is False
        assert results == []

    def test_render_readme(self, tmp_path: Path) -> None:
        config = self._make_config([
            FeedConfig(
                name="RenderFeed",
                url="https://example.com/feed.xml",
                section_marker="RENDER_FEED",
                max_posts=2,
                enabled=True,
            )
        ])
        readme_path = self._make_readme(
            tmp_path, "# README\n\n<!-- RENDER_FEED_START -->\nOld\n<!-- RENDER_FEED_END -->\n",
        )
        articles = [
            Article(title="A", link="https://a.com", date="2024-01-01"),
            Article(title="B", link="https://b.com", date="2024-01-02"),
        ]

        updater = RSSUpdater(config)
        with (
            patch.object(updater.fetcher, "fetch", return_value=articles),
            patch.object(updater.detector, "detect_changes", return_value=(True, articles, "hash1")),
            patch("rss_updater.updater.send_notifications"),
        ):
            updated, results = updater.update_readme(readme_path)

        assert updated is True
        new_content = Path(readme_path).read_text(encoding="utf-8")
        assert "A" in new_content
        assert "B" in new_content
        assert "Old" not in new_content

    def test_render_readme_fetch_error(self, tmp_path: Path) -> None:
        config = self._make_config([
            FeedConfig(
                name="RenderFeed",
                url="https://example.com/feed.xml",
                section_marker="RENDER_FEED",
                max_posts=2,
                enabled=True,
            )
        ])
        readme_path = self._make_readme(
            tmp_path, "# README\n\n<!-- RENDER_FEED_START -->\nOld\n<!-- RENDER_FEED_END -->\n",
        )

        updater = RSSUpdater(config)
        with patch.object(updater.fetcher, "fetch", return_value=None):
            updated, results = updater.update_readme(readme_path)

        assert updated is False
        assert results[0].status == "error"

    def test_atomic_write_failure(self, tmp_path: Path) -> None:
        target = tmp_path / "output.md"
        with patch("rss_updater.updater.os.fdopen", side_effect=OSError("disk full")), pytest.raises(OSError):
            RSSUpdater._atomic_write(target, "hello world")

    def test_run_exception(self, tmp_path: Path) -> None:
        config = self._make_config()
        updater = RSSUpdater(config)
        with patch.object(updater, "update_readme", side_effect=Exception("unexpected")):
            assert updater.run() == 1
