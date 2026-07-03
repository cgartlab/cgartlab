from __future__ import annotations

import abc
import asyncio
import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from rss_updater.models import Article, NotificationChannel

logger = logging.getLogger("rss_updater.notifier")

# Retry config shared across all notifier HTTP calls
_RETRY_CONFIG = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist={429, 500, 502, 503, 504},
    allowed_methods=["GET", "POST"],
)

# Default timeout for notification HTTP calls (seconds)
_DEFAULT_NOTIFY_TIMEOUT = 30.0


def _http_session() -> requests.Session:
    """Return a requests Session with retry logic pre-configured."""
    session = requests.Session()
    session.mount("http://", HTTPAdapter(max_retries=_RETRY_CONFIG))
    session.mount("https://", HTTPAdapter(max_retries=_RETRY_CONFIG))
    return session


class BaseNotifier(abc.ABC):
    def __init__(self, config: NotificationChannel) -> None:
        self.config = config

    @abc.abstractmethod
    async def notify(self, feed_name: str, new_articles: list[Article]) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError


def _get_config_value(config: NotificationChannel, key: str) -> str:
    val = getattr(config, key, None)
    if isinstance(val, str):
        return val
    extra = config.model_extra or {}
    extra_val = extra.get(key, "")
    return extra_val if isinstance(extra_val, str) else ""


class WebhookNotifier(BaseNotifier):
    async def notify(self, feed_name: str, new_articles: list[Article]) -> None:
        if not self.is_configured():
            logger.debug("WebhookNotifier not configured, skipping")
            return
        webhook_url = _get_config_value(self.config, "webhook_url")
        payload: dict[str, Any] = {
            "feed_name": feed_name,
            "articles": [a.model_dump() for a in new_articles],
            "count": len(new_articles),
        }
        try:
            session = _http_session()
            response = session.post(webhook_url, json=payload, timeout=_DEFAULT_NOTIFY_TIMEOUT)
            response.raise_for_status()
            logger.info("Webhook notification sent to %s for %s", webhook_url, feed_name)
        except Exception:
            logger.exception("Failed to send webhook notification to %s", webhook_url)

    def is_configured(self) -> bool:
        return bool(_get_config_value(self.config, "webhook_url"))


class TelegramNotifier(BaseNotifier):
    async def notify(self, feed_name: str, new_articles: list[Article]) -> None:
        if not self.is_configured():
            logger.debug("TelegramNotifier not configured, skipping")
            return
        token = _get_config_value(self.config, "telegram_token")
        chat_id = _get_config_value(self.config, "telegram_chat_id")
        api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        titles = "\n".join(f"- {a.title}" for a in new_articles[:10])
        text = f"*{feed_name}* 更新了 {len(new_articles)} 篇文章:\n\n{titles}"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        try:
            session = _http_session()
            response = session.post(api_url, json=payload, timeout=_DEFAULT_NOTIFY_TIMEOUT)
            response.raise_for_status()
            logger.info("Telegram notification sent for %s", feed_name)
        except Exception:
            logger.exception("Failed to send Telegram notification for %s", feed_name)

    def is_configured(self) -> bool:
        token = _get_config_value(self.config, "telegram_token")
        chat_id = _get_config_value(self.config, "telegram_chat_id")
        return bool(token) and bool(chat_id)


class BarkNotifier(BaseNotifier):
    async def notify(self, feed_name: str, new_articles: list[Article]) -> None:
        if not self.is_configured():
            logger.debug("BarkNotifier not configured, skipping")
            return
        key = _get_config_value(self.config, "bark_key")
        title = f"{feed_name} 更新"
        body = "\n".join(a.title for a in new_articles[:5])
        # Token as query param instead of URL path — avoids token leaking in logs/traces
        params = {"title": title, "body": body}
        url = f"https://api.day.app/{key}"
        try:
            session = _http_session()
            response = session.get(url, params=params, timeout=_DEFAULT_NOTIFY_TIMEOUT)
            response.raise_for_status()
            logger.info("Bark notification sent for %s", feed_name)
        except Exception:
            logger.exception("Failed to send Bark notification for %s", feed_name)

    def is_configured(self) -> bool:
        return bool(_get_config_value(self.config, "bark_key"))


class NotifierRegistry:
    _registry: dict[str, type[BaseNotifier]] = {}

    @classmethod
    def register(cls, type_name: str, notifier_cls: type[BaseNotifier]) -> None:
        cls._registry[type_name] = notifier_cls

    @classmethod
    def create(cls, channel: NotificationChannel) -> BaseNotifier:
        notifier_cls = cls._registry.get(channel.type)
        if notifier_cls is None:
            raise ValueError(f"Unknown notification type: {channel.type}")
        return notifier_cls(channel)

    @classmethod
    def _ensure_builtin(cls) -> None:
        if not cls._registry:
            cls.register("webhook", WebhookNotifier)
            cls.register("telegram", TelegramNotifier)
            cls.register("bark", BarkNotifier)


NotifierRegistry._ensure_builtin()


def send_notifications(
    channels: list[NotificationChannel],
    feed_name: str,
    new_articles: list[Article],
) -> None:
    if not new_articles:
        return

    async def _send() -> None:
        tasks: list[asyncio.Task[None]] = []
        for channel in channels:
            if not channel.enabled:
                continue
            try:
                notifier = NotifierRegistry.create(channel)
            except ValueError:
                logger.warning("Skipping unknown notification channel type: %s", channel.type)
                continue
            if notifier.is_configured():
                tasks.append(asyncio.create_task(notifier.notify(feed_name, new_articles)))
            else:
                logger.debug("Notifier %s not configured, skipping", channel.type)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(_send())
