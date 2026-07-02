from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from rss_updater.models import AppConfig, Article, CheckResult, FeedConfig, Settings


@pytest.fixture
def sample_article() -> Article:
    return Article(
        title="Test Title",
        link="https://example.com",
        date="2024-01-01",
        description="A description",
        author="Alice",
        guid="guid-123",
    )


@pytest.fixture
def sample_articles() -> list[Article]:
    return [
        Article(title="Title 1", link="https://example.com/1", date="2024-01-01", guid="g1"),
        Article(title="Title 2", link="https://example.com/2", date="2024-01-02", guid="g2"),
    ]


@pytest.fixture
def feed_config() -> FeedConfig:
    return FeedConfig(
        name="Test Feed",
        url="https://example.com/rss",
        section_marker="MARKER",
        max_posts=5,
        enabled=True,
    )


@pytest.fixture
def app_config() -> AppConfig:
    return AppConfig(
        feeds=[
            FeedConfig(
                name="Test Feed",
                url="https://example.com/rss",
                section_marker="MARKER",
                max_posts=5,
                enabled=True,
            )
        ],
        settings=Settings(
            check_interval_minutes=60,
            max_retries=3,
            timeout_seconds=15.0,
            history_dir=".rss_history",
            log_level="INFO",
        ),
    )


@pytest.fixture
def check_result() -> CheckResult:
    return CheckResult(
        status="success",
        timestamp="2024-01-01T00:00:00+00:00",
        feed_name="TestFeed",
        articles_count=2,
        new_articles=[
            Article(title="Title 1", link="https://example.com/1", date="2024-01-01", guid="g1"),
        ],
    )


@pytest.fixture
def config_data_old_style() -> dict[str, Any]:
    return {
        "feeds": [
            {
                "name": "Old Blog",
                "url": "https://old.example.com/rss",
                "section_marker": "OLD_START",
                "max_posts": 3,
                "enabled": True,
            }
        ],
        "settings": {
            "check_interval_minutes": 30,
            "max_retries": 2,
            "timeout_seconds": 10.0,
            "history_dir": ".history",
            "log_level": "DEBUG",
        },
        "notifications": {
            "telegram": {"enabled": True, "token": "abc123", "chat_id": "-100"},
            "webhook": {"enabled": False, "url": "https://hook.example.com"},
        },
    }


@pytest.fixture
def config_data_new_style() -> dict[str, Any]:
    return {
        "feeds": [
            {
                "name": "New Blog",
                "url": "https://new.example.com/rss",
                "section_marker": "NEW_START",
                "max_posts": 5,
                "enabled": True,
            }
        ],
        "settings": {
            "check_interval_minutes": 60,
            "max_retries": 3,
            "timeout_seconds": 15.0,
            "history_dir": ".rss_history",
            "log_level": "INFO",
        },
        "notifications": {
            "channels": [
                {"type": "email", "enabled": True, "smtp_host": "smtp.example.com"},
                {"type": "slack", "enabled": False, "webhook_url": "https://hooks.slack.com"},
            ]
        },
    }


@pytest.fixture
def config_path(tmp_path: Path, config_data_old_style: dict[str, Any]) -> Path:
    path = tmp_path / "rss_config.json"
    path.write_text(json.dumps(config_data_old_style), encoding="utf-8")
    return path
