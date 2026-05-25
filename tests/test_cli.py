from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from rss_updater.cli import _build_parser, _health_check, main
from rss_updater.models import AppConfig, FeedConfig, Settings


class TestCLIArgumentParsing:
    def test_default_args(self) -> None:
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.config == "rss_config.json"
        assert args.check_mode is False
        assert args.force is False
        assert args.verbose is False
        assert args.health_check is False

    def test_config_short(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["-c", "my_config.json"])
        assert args.config == "my_config.json"

    def test_config_long(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--config", "my_config.json"])
        assert args.config == "my_config.json"

    def test_check_mode(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--check-mode"])
        assert args.check_mode is True

    def test_force_short(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["-f"])
        assert args.force is True

    def test_verbose(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["-v"])
        assert args.verbose is True

    def test_health_check(self) -> None:
        parser = _build_parser()
        args = parser.parse_args(["--health-check"])
        assert args.health_check is True


class TestCLIMain:
    def test_main_loads_config_and_runs(self, tmp_path: Path) -> None:
        config_path = tmp_path / "rss_config.json"
        config_data = {
            "feeds": [
                {
                    "name": "Test",
                    "url": "https://example.com/feed.xml",
                    "section_marker": "TEST",
                    "enabled": True,
                }
            ],
            "settings": {"history_dir": str(tmp_path / ".history")},
        }
        config_path.write_text(json.dumps(config_data), encoding="utf-8")
        readme = tmp_path / "README.md"
        readme.write_text("# README\n", encoding="utf-8")

        with patch("rss_updater.cli.RSSUpdater") as mock_updater_cls:
            mock_updater = MagicMock()
            mock_updater.run.return_value = 0
            mock_updater_cls.return_value = mock_updater
            ret = main(["-c", str(config_path)])

        assert ret == 0
        mock_updater_cls.assert_called_once()
        call_kwargs = mock_updater_cls.call_args[1]
        assert call_kwargs["check_mode"] is False
        assert call_kwargs["force"] is False

    def test_main_check_mode(self, tmp_path: Path) -> None:
        config_path = tmp_path / "rss_config.json"
        config_data = {
            "feeds": [],
            "settings": {"history_dir": str(tmp_path / ".history")},
        }
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        with patch("rss_updater.cli.RSSUpdater") as mock_updater_cls:
            mock_updater = MagicMock()
            mock_updater.run.return_value = 0
            mock_updater_cls.return_value = mock_updater
            ret = main(["-c", str(config_path), "--check-mode"])

        assert ret == 0
        call_kwargs = mock_updater_cls.call_args[1]
        assert call_kwargs["check_mode"] is True

    def test_main_force_mode(self, tmp_path: Path) -> None:
        config_path = tmp_path / "rss_config.json"
        config_data = {
            "feeds": [],
            "settings": {"history_dir": str(tmp_path / ".history")},
        }
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        with patch("rss_updater.cli.RSSUpdater") as mock_updater_cls:
            mock_updater = MagicMock()
            mock_updater.run.return_value = 0
            mock_updater_cls.return_value = mock_updater
            ret = main(["-c", str(config_path), "-f"])

        assert ret == 0
        call_kwargs = mock_updater_cls.call_args[1]
        assert call_kwargs["force"] is True

    def test_main_config_load_error(self, tmp_path: Path, capsys: Any) -> None:
        config_path = tmp_path / "nonexistent.json"
        ret = main(["-c", str(config_path)])
        assert ret == 1
        captured = capsys.readouterr()
        assert "Failed to load config" in captured.err


class TestSetupStdoutUtf8:
    def test_setup_stdout_utf8_on_windows(self):
        from rss_updater.cli import _setup_stdout_utf8

        with patch.object(sys, "platform", "win32"):
            _setup_stdout_utf8()

    def test_setup_stdout_utf8_attribute_error(self):
        from rss_updater.cli import _setup_stdout_utf8

        with patch.object(sys, "platform", "win32"):
            fake_stdout = MagicMock()
            fake_stdout.reconfigure.side_effect = AttributeError("no reconfigure")
            with patch.object(sys, "stdout", fake_stdout), patch.object(sys, "stderr", fake_stdout):
                _setup_stdout_utf8()


class TestMainHealthCheck:
    def test_main_health_check_flag(self, tmp_path: Path, capsys: Any) -> None:
        config_path = tmp_path / "rss_config.json"
        config_data = {
            "feeds": [
                {
                    "name": "HealthFeed",
                    "url": "https://example.com/feed.xml",
                    "section_marker": "HEALTH",
                    "enabled": True,
                }
            ],
            "settings": {"history_dir": str(tmp_path / ".history")},
        }
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        with patch("rss_updater.cli.FeedFetcher") as mock_fetcher_cls:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = [MagicMock()]
            mock_fetcher_cls.return_value = mock_fetcher
            ret = main(["-c", str(config_path), "--health-check"])

        assert ret == 0
        captured = capsys.readouterr()
        assert "HealthFeed" in captured.out
        assert "ok" in captured.out


class TestHealthCheck:
    def test_health_check_success(self, capsys: Any) -> None:
        config = AppConfig(
            feeds=[
                FeedConfig(
                    name="TestFeed",
                    url="https://example.com/feed.xml",
                    section_marker="TEST",
                    enabled=True,
                )
            ],
            settings=Settings(),
        )
        articles = [MagicMock()]

        with patch("rss_updater.cli.FeedFetcher") as mock_fetcher_cls:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = articles
            mock_fetcher_cls.return_value = mock_fetcher
            ret = _health_check(config)

        assert ret == 0
        captured = capsys.readouterr()
        assert "TestFeed" in captured.out
        assert "ok" in captured.out

    def test_health_check_failure(self, capsys: Any) -> None:
        config = AppConfig(
            feeds=[
                FeedConfig(
                    name="BadFeed",
                    url="https://bad.example.com/feed.xml",
                    section_marker="BAD",
                    enabled=True,
                )
            ],
            settings=Settings(),
        )

        with patch("rss_updater.cli.FeedFetcher") as mock_fetcher_cls:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.return_value = None
            mock_fetcher_cls.return_value = mock_fetcher
            ret = _health_check(config)

        assert ret == 0
        captured = capsys.readouterr()
        assert "BadFeed" in captured.out
        assert "fail" in captured.out

    def test_health_check_exception(self, capsys: Any) -> None:
        config = AppConfig(
            feeds=[
                FeedConfig(
                    name="ErrFeed",
                    url="https://err.example.com/feed.xml",
                    section_marker="ERR",
                    enabled=True,
                )
            ],
            settings=Settings(),
        )

        with patch("rss_updater.cli.FeedFetcher") as mock_fetcher_cls:
            mock_fetcher = MagicMock()
            mock_fetcher.fetch.side_effect = Exception("timeout")
            mock_fetcher_cls.return_value = mock_fetcher
            ret = _health_check(config)

        assert ret == 0
        captured = capsys.readouterr()
        assert "ErrFeed" in captured.out
        assert "error" in captured.out
        assert "timeout" in captured.out

    def test_health_check_skips_disabled(self, capsys: Any) -> None:
        config = AppConfig(
            feeds=[
                FeedConfig(
                    name="Disabled",
                    url="https://example.com/feed.xml",
                    section_marker="DIS",
                    enabled=False,
                )
            ],
            settings=Settings(),
        )

        with patch("rss_updater.cli.FeedFetcher") as mock_fetcher_cls:
            mock_fetcher = MagicMock()
            mock_fetcher_cls.return_value = mock_fetcher
            ret = _health_check(config)

        assert ret == 0
        captured = capsys.readouterr()
        assert "Disabled" not in captured.out
        mock_fetcher.fetch.assert_not_called()
