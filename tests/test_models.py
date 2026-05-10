import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from rss_updater.models import (
    Article,
    CheckResult,
    FeedConfig,
    load_config,
)


class TestArticle:
    def test_serialization_roundtrip(self):
        article = Article(
            title="Test Title",
            link="https://example.com",
            date="2024-01-01",
            description="A description",
            author="Alice",
            guid="guid-123",
        )
        data = article.model_dump()
        restored = Article.model_validate(data)
        assert restored.title == "Test Title"
        assert restored.link == "https://example.com"
        assert restored.date == "2024-01-01"
        assert restored.description == "A description"
        assert restored.author == "Alice"
        assert restored.guid == "guid-123"

    def test_deserialization_with_defaults(self):
        data = {"title": "Minimal", "link": "https://example.com"}
        article = Article.model_validate(data)
        assert article.date == "未知日期"
        assert article.description == ""
        assert article.author == ""
        assert article.guid == ""


class TestFeedConfig:
    def test_max_posts_negative_raises(self):
        with pytest.raises(ValidationError) as exc_info:
            FeedConfig(
                name="Test Feed",
                url="https://example.com/rss",
                section_marker="MARKER",
                max_posts=-1,
            )
        assert "max_posts" in str(exc_info.value)


class TestCheckResult:
    def test_status_validation_error(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            CheckResult(
                status="invalid_status",
                timestamp="2024-01-01T00:00:00+00:00",
                feed_name="TestFeed",
                articles_count=0,
                new_articles=[],
            )
        assert "status" in str(exc_info.value)


class TestLoadConfig:
    def test_load_old_style_dict_notifications(self, tmp_path: Path):
        config_path = tmp_path / "rss_config_old.json"
        config_data = {
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
                "telegram": {
                    "enabled": True,
                    "token": "abc123",
                    "chat_id": "-100",
                },
                "webhook": {
                    "enabled": False,
                    "url": "https://hook.example.com",
                },
            },
        }
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        app_config = load_config(str(config_path))
        assert len(app_config.feeds) == 1
        assert app_config.feeds[0].name == "Old Blog"
        assert len(app_config.notifications) == 2
        types = {n.type for n in app_config.notifications}
        assert types == {"telegram", "webhook"}
        telegram = next(n for n in app_config.notifications if n.type == "telegram")
        assert telegram.enabled is True
        assert telegram.model_extra is not None
        assert telegram.model_extra.get("token") == "abc123"
        assert telegram.model_extra.get("chat_id") == "-100"

    def test_load_new_style_list_notifications(self, tmp_path: Path):
        config_path = tmp_path / "rss_config_new.json"
        config_data = {
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
                    {
                        "type": "email",
                        "enabled": True,
                        "smtp_host": "smtp.example.com",
                    },
                    {
                        "type": "slack",
                        "enabled": False,
                        "webhook_url": "https://hooks.slack.com",
                    },
                ]
            },
        }
        config_path.write_text(json.dumps(config_data), encoding="utf-8")

        app_config = load_config(str(config_path))
        assert len(app_config.feeds) == 1
        assert app_config.feeds[0].name == "New Blog"
        assert len(app_config.notifications) == 2
        types = {n.type for n in app_config.notifications}
        assert types == {"email", "slack"}
        email = next(n for n in app_config.notifications if n.type == "email")
        assert email.enabled is True
        assert email.model_extra is not None
        assert email.model_extra.get("smtp_host") == "smtp.example.com"
