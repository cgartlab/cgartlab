from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Article(BaseModel):
    title: str
    link: str
    date: str = "未知日期"
    description: str = ""
    author: str = ""
    guid: str = ""


class CheckResult(BaseModel):
    status: str
    timestamp: str
    feed_name: str
    articles_count: int
    new_articles: list[Article]
    error_message: str | None = None
    content_hash: str | None = None

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        allowed = {"success", "error", "no_change", "partial"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}, got {v!r}")
        return v


class FeedConfig(BaseModel):
    name: str
    url: str
    section_marker: str
    max_posts: int = Field(default=5, ge=1)
    enabled: bool = True


class Settings(BaseModel):
    check_interval_minutes: int = Field(default=60, ge=1)
    max_retries: int = Field(default=3, ge=0)
    timeout_seconds: float = Field(default=15.0, gt=0)
    history_dir: str = ".rss_history"
    log_level: str = "INFO"


class NotificationChannel(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    enabled: bool = True


class AppConfig(BaseModel):
    feeds: list[FeedConfig]
    settings: Settings = Field(default_factory=Settings)
    notifications: list[NotificationChannel] = Field(default_factory=list)


def load_config(path: str) -> AppConfig:
    with open(path, encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    raw_notifications = data.get("notifications")
    if isinstance(raw_notifications, dict):
        if "channels" in raw_notifications:
            data["notifications"] = raw_notifications["channels"]
        else:
            # 旧版扁平结构：跳过非 dict 值（如 enabled: false）
            channels = []
            for k, v in raw_notifications.items():
                if isinstance(v, dict):
                    channels.append({"type": k, **v})
            data["notifications"] = channels
    elif raw_notifications is None:
        data["notifications"] = []

    return AppConfig.model_validate(data)

