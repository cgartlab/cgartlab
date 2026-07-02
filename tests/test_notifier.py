from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from rss_updater.models import Article, NotificationChannel
from rss_updater.notifier import (
    BarkNotifier,
    BaseNotifier,
    NotifierRegistry,
    TelegramNotifier,
    WebhookNotifier,
    send_notifications,
)


class TestBaseNotifier:
    def test_base_notifier_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            BaseNotifier(config=MagicMock())


class TestWebhookNotifier:
    def test_is_configured_true(self) -> None:
        config = NotificationChannel(type="webhook", webhook_url="https://example.com/hook")
        notifier = WebhookNotifier(config)
        assert notifier.is_configured() is True

    def test_is_configured_false(self) -> None:
        config = NotificationChannel(type="webhook", webhook_url="")
        notifier = WebhookNotifier(config)
        assert notifier.is_configured() is False

    def test_notify_sends_correct_payload(self) -> None:
        config = NotificationChannel(type="webhook", webhook_url="https://example.com/hook")
        notifier = WebhookNotifier(config)
        articles = [
            Article(title="A", link="https://a.com", date="2024-01-01"),
            Article(title="B", link="https://b.com", date="2024-01-02"),
        ]

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_session.post.return_value = mock_response
        with patch("rss_updater.notifier._http_session", return_value=mock_session):
            asyncio.run(notifier.notify("TestFeed", articles))

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "https://example.com/hook"
        payload = call_args[1]["json"]
        assert payload["feed_name"] == "TestFeed"
        assert payload["count"] == 2
        assert len(payload["articles"]) == 2
        assert payload["articles"][0]["title"] == "A"

    def test_notify_skips_when_not_configured(self) -> None:
        config = NotificationChannel(type="webhook", webhook_url="")
        notifier = WebhookNotifier(config)
        mock_session = MagicMock()
        with patch("rss_updater.notifier._http_session", return_value=mock_session):
            asyncio.run(notifier.notify("TestFeed", [Article(title="A", link="https://a.com")]))
        mock_session.post.assert_not_called()


class TestTelegramNotifier:
    def test_is_configured_true(self) -> None:
        config = NotificationChannel(type="telegram", telegram_token="tok", telegram_chat_id="123")
        notifier = TelegramNotifier(config)
        assert notifier.is_configured() is True

    def test_is_configured_false_missing_token(self) -> None:
        config = NotificationChannel(type="telegram", telegram_token="", telegram_chat_id="123")
        notifier = TelegramNotifier(config)
        assert notifier.is_configured() is False

    def test_is_configured_false_missing_chat_id(self) -> None:
        config = NotificationChannel(type="telegram", telegram_token="tok", telegram_chat_id="")
        notifier = TelegramNotifier(config)
        assert notifier.is_configured() is False

    def test_notify_constructs_correct_api_url_and_payload(self) -> None:
        config = NotificationChannel(type="telegram", telegram_token="mytoken", telegram_chat_id="456")
        notifier = TelegramNotifier(config)
        articles = [Article(title="Article 1", link="https://a.com", date="2024-01-01")]

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_session.post.return_value = mock_response
        with patch("rss_updater.notifier._http_session", return_value=mock_session):
            asyncio.run(notifier.notify("MyFeed", articles))

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[0][0] == "https://api.telegram.org/botmytoken/sendMessage"
        payload = call_args[1]["json"]
        assert payload["chat_id"] == "456"
        assert "MyFeed" in payload["text"]
        assert "Article 1" in payload["text"]
        assert payload["parse_mode"] == "Markdown"

    def test_notify_skips_when_not_configured(self) -> None:
        config = NotificationChannel(type="telegram", telegram_token="", telegram_chat_id="")
        notifier = TelegramNotifier(config)
        mock_session = MagicMock()
        with patch("rss_updater.notifier._http_session", return_value=mock_session):
            asyncio.run(notifier.notify("MyFeed", [Article(title="A", link="https://a.com")]))
        mock_session.post.assert_not_called()


class TestBarkNotifier:
    def test_is_configured_true(self) -> None:
        config = NotificationChannel(type="bark", bark_key="mykey")
        notifier = BarkNotifier(config)
        assert notifier.is_configured() is True

    def test_is_configured_false(self) -> None:
        config = NotificationChannel(type="bark", bark_key="")
        notifier = BarkNotifier(config)
        assert notifier.is_configured() is False

    def test_notify_constructs_correct_url(self) -> None:
        config = NotificationChannel(type="bark", bark_key="mykey")
        notifier = BarkNotifier(config)
        articles = [
            Article(title="Hello", link="https://a.com", date="2024-01-01"),
            Article(title="World", link="https://b.com", date="2024-01-02"),
        ]

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_session.get.return_value = mock_response
        with patch("rss_updater.notifier._http_session", return_value=mock_session):
            asyncio.run(notifier.notify("Feed", articles))

        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert call_args[0][0] == "https://api.day.app/mykey"
        params = call_args[1]["params"]
        assert params["title"] == "Feed 更新"
        assert "Hello" in params["body"]
        assert "World" in params["body"]

    def test_notify_skips_when_not_configured(self) -> None:
        config = NotificationChannel(type="bark", bark_key="")
        notifier = BarkNotifier(config)
        mock_session = MagicMock()
        with patch("rss_updater.notifier._http_session", return_value=mock_session):
            asyncio.run(notifier.notify("Feed", [Article(title="A", link="https://a.com")]))
        mock_session.get.assert_not_called()


class TestNotifierExceptions:
    def test_webhook_notify_exception(self) -> None:
        config = NotificationChannel(type="webhook", webhook_url="https://example.com/hook")
        notifier = WebhookNotifier(config)
        articles = [Article(title="A", link="https://a.com", date="2024-01-01")]

        mock_session = MagicMock()
        mock_session.post.side_effect = Exception("network error")
        with patch("rss_updater.notifier._http_session", return_value=mock_session):
            asyncio.run(notifier.notify("TestFeed", articles))

    def test_telegram_notify_exception(self) -> None:
        config = NotificationChannel(type="telegram", telegram_token="tok", telegram_chat_id="123")
        notifier = TelegramNotifier(config)
        articles = [Article(title="A", link="https://a.com", date="2024-01-01")]

        mock_session = MagicMock()
        mock_session.post.side_effect = Exception("network error")
        with patch("rss_updater.notifier._http_session", return_value=mock_session):
            asyncio.run(notifier.notify("TestFeed", articles))

    def test_bark_notify_exception(self) -> None:
        config = NotificationChannel(type="bark", bark_key="mykey")
        notifier = BarkNotifier(config)
        articles = [Article(title="A", link="https://a.com", date="2024-01-01")]

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("network error")
        with patch("rss_updater.notifier._http_session", return_value=mock_session):
            asyncio.run(notifier.notify("TestFeed", articles))


class TestNotifierRegistry:
    def test_register_and_create(self) -> None:
        class DummyNotifier(BaseNotifier):
            async def notify(self, feed_name: str, new_articles: list[Article]) -> None:
                pass

            def is_configured(self) -> bool:
                return True

        NotifierRegistry.register("dummy", DummyNotifier)
        channel = NotificationChannel(type="dummy")
        notifier = NotifierRegistry.create(channel)
        assert isinstance(notifier, DummyNotifier)

    def test_create_builtin_webhook(self) -> None:
        channel = NotificationChannel(type="webhook", webhook_url="https://example.com")
        notifier = NotifierRegistry.create(channel)
        assert isinstance(notifier, WebhookNotifier)

    def test_create_builtin_telegram(self) -> None:
        channel = NotificationChannel(type="telegram", telegram_token="t", telegram_chat_id="1")
        notifier = NotifierRegistry.create(channel)
        assert isinstance(notifier, TelegramNotifier)

    def test_create_builtin_bark(self) -> None:
        channel = NotificationChannel(type="bark", bark_key="k")
        notifier = NotifierRegistry.create(channel)
        assert isinstance(notifier, BarkNotifier)

    def test_create_unknown_type_raises(self) -> None:
        channel = NotificationChannel(type="unknown")
        with pytest.raises(ValueError, match="Unknown notification type"):
            NotifierRegistry.create(channel)


class TestSendNotifications:
    def test_send_notifications_runs_notifiers(self) -> None:
        channel = NotificationChannel(type="webhook", webhook_url="https://example.com/hook")
        articles = [Article(title="A", link="https://a.com", date="2024-01-01")]

        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_session.post.return_value = mock_response
        with patch("rss_updater.notifier._http_session", return_value=mock_session):
            send_notifications([channel], "Feed", articles)

        mock_session.post.assert_called_once()

    def test_send_notifications_skips_disabled_channels(self) -> None:
        channel = NotificationChannel(type="webhook", enabled=False, webhook_url="https://example.com/hook")
        articles = [Article(title="A", link="https://a.com", date="2024-01-01")]

        with patch("rss_updater.notifier._http_session") as mock_hs:
            send_notifications([channel], "Feed", articles)

        mock_hs.return_value.post.assert_not_called()

    def test_send_notifications_skips_empty_articles(self) -> None:
        channel = NotificationChannel(type="webhook", webhook_url="https://example.com/hook")
        articles: list[Article] = []
        with patch("rss_updater.notifier._http_session") as mock_hs:
            send_notifications([channel], "Feed", articles)

        mock_hs.return_value.post.assert_not_called()


class TestHttpSession:
    def test_http_session_creates_configured_session(self) -> None:
        from rss_updater.notifier import _http_session

        session = _http_session()
        try:
            assert session is not None
            assert hasattr(session, "get")
            assert hasattr(session, "post")
            adapters = session.adapters
            assert "https://" in adapters
            assert "http://" in adapters
        finally:
            session.close()

    def test_http_session_closeable(self) -> None:
        from rss_updater.notifier import _http_session

        session = _http_session()
        session.close()
        assert True

    def test_send_notifications_skips_unconfigured(self) -> None:
        channel = NotificationChannel(type="webhook", webhook_url="")
        articles = [Article(title="A", link="https://a.com", date="2024-01-01")]

        with patch("rss_updater.notifier._http_session") as mock_hs:
            send_notifications([channel], "Feed", articles)

        mock_hs.return_value.post.assert_not_called()

    def test_send_notifications_skips_unknown_type(self) -> None:
        channel = NotificationChannel(type="unknown_type_xyz")
        articles = [Article(title="A", link="https://a.com", date="2024-01-01")]

        with patch("rss_updater.notifier._http_session") as mock_hs:
            send_notifications([channel], "Feed", articles)

        mock_hs.return_value.post.assert_not_called()
