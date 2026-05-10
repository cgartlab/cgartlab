from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, patch

from rss_updater.fetcher import FeedFetcher
from rss_updater.models import Article


class MockResponse:
    def __init__(self, content: bytes = b"", status_code: int = 200, raise_error: bool = False) -> None:
        self.content = content
        self.status_code = status_code
        self._raise_error = raise_error

    def raise_for_status(self) -> None:
        if self._raise_error:
            raise Exception("HTTP Error")


class TestFeedFetcher:
    def test_build_headers(self) -> None:
        fetcher = FeedFetcher()
        headers = fetcher._build_headers("https://example.com/feed.xml")
        assert "User-Agent" in headers
        assert "Chrome/120.0.0.0" in headers["User-Agent"]
        assert headers["Referer"] == "https://example.com/feed.xml"

    def test_create_session_has_retry(self) -> None:
        fetcher = FeedFetcher()
        session = fetcher._create_session()
        assert "https://" in session.adapters
        adapter = session.get_adapter("https://example.com")
        assert adapter.max_retries.total == 3

    def test_parse_date_with_published_parsed(self) -> None:
        entry: dict[str, Any] = {"published_parsed": time.struct_time((2024, 6, 15, 0, 0, 0, 0, 167, 0))}
        assert FeedFetcher._parse_date(entry) == "2024-06-15"

    def test_parse_date_with_updated_parsed_fallback(self) -> None:
        entry: dict[str, Any] = {"updated_parsed": time.struct_time((2023, 1, 1, 0, 0, 0, 0, 1, 0))}
        assert FeedFetcher._parse_date(entry) == "2023-01-01"

    def test_parse_date_with_created_parsed_fallback(self) -> None:
        entry: dict[str, Any] = {"created_parsed": time.struct_time((2022, 12, 31, 0, 0, 0, 0, 365, 0))}
        assert FeedFetcher._parse_date(entry) == "2022-12-31"

    def test_parse_date_unknown(self) -> None:
        entry: dict[str, Any] = {}
        assert FeedFetcher._parse_date(entry) == "未知日期"

    def test_parse_date_invalid_struct_time(self) -> None:
        entry: dict[str, Any] = {"published_parsed": "not-a-time"}
        assert FeedFetcher._parse_date(entry) == "未知日期"

    def test_session_property_creates_session(self) -> None:
        fetcher = FeedFetcher()
        assert fetcher._session is None
        session = fetcher.session
        assert session is not None
        assert fetcher._session is session
        assert fetcher.session is session

    def test_entry_to_article(self) -> None:
        fetcher = FeedFetcher()
        entry: dict[str, Any] = {
            "title": "Test Title",
            "link": "https://example.com/post",
            "published_parsed": time.struct_time((2024, 1, 1, 0, 0, 0, 0, 1, 0)),
            "description": "A description",
            "author": "Alice",
            "id": "guid-123",
        }
        article = fetcher._entry_to_article(entry)
        assert article.title == "Test Title"
        assert article.link == "https://example.com/post"
        assert article.date == "2024-01-01"
        assert article.description == "A description"
        assert article.author == "Alice"
        assert article.guid == "guid-123"

    def test_entry_to_article_fallback_guid(self) -> None:
        fetcher = FeedFetcher()
        entry: dict[str, Any] = {
            "title": "T",
            "link": "https://example.com/post",
        }
        article = fetcher._entry_to_article(entry)
        assert article.guid == "https://example.com/post"

    def test_fetch_direct_success(self) -> None:
        mock_session = MagicMock()
        rss_content = b"""<?xml version="1.0"?>
<rss version="2.0">
<channel>
<item><title>Direct</title><link>https://example.com/1</link><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item>
</channel>
</rss>"""
        mock_session.get.return_value = MockResponse(content=rss_content)
        fetcher = FeedFetcher(session=mock_session)
        articles = fetcher._fetch_direct(mock_session, "https://example.com/feed", {}, 15.0)
        assert articles is not None
        assert len(articles) == 1
        assert articles[0].title == "Direct"

    def test_fetch_direct_failure(self) -> None:
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection error")
        fetcher = FeedFetcher(session=mock_session)
        articles = fetcher._fetch_direct(mock_session, "https://example.com/feed", {}, 15.0)
        assert articles is None

    def test_fetch_via_proxy_success(self) -> None:
        mock_session = MagicMock()
        rss_content = b"""<?xml version="1.0"?>
<rss version="2.0">
<channel>
<item><title>Proxy</title><link>https://example.com/2</link><pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate></item>
</channel>
</rss>"""
        mock_session.get.return_value = MockResponse(content=rss_content)
        fetcher = FeedFetcher(session=mock_session)
        articles = fetcher._fetch_via_proxy(mock_session, "https://example.com/feed", {}, 15.0)
        assert articles is not None
        assert len(articles) == 1
        assert articles[0].title == "Proxy"
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        assert "r.jina.ai" in call_args[0][0]

    def test_fetch_via_proxy_failure(self) -> None:
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Proxy error")
        fetcher = FeedFetcher(session=mock_session)
        articles = fetcher._fetch_via_proxy(mock_session, "https://example.com/feed", {}, 15.0)
        assert articles is None

    @patch("rss_updater.fetcher.feedparser.parse")
    def test_fetch_feedparser_direct_success(self, mock_parse: Any) -> None:
        mock_parse.return_value = MagicMock(
            entries=[
                {
                    "title": "FP",
                    "link": "https://example.com/3",
                    "published_parsed": time.struct_time((2024, 3, 1, 0, 0, 0, 0, 61, 0)),
                }
            ]
        )
        fetcher = FeedFetcher()
        articles = fetcher._fetch_feedparser_direct("https://example.com/feed")
        assert articles is not None
        assert len(articles) == 1
        assert articles[0].title == "FP"

    @patch("rss_updater.fetcher.feedparser.parse")
    def test_fetch_feedparser_direct_failure(self, mock_parse: Any) -> None:
        mock_parse.side_effect = Exception("Parse error")
        fetcher = FeedFetcher()
        articles = fetcher._fetch_feedparser_direct("https://example.com/feed")
        assert articles is None

    def test_fetch_direct_then_proxy_fallback(self) -> None:
        mock_session = MagicMock()
        rss_content = b"""<?xml version="1.0"?>
<rss version="2.0">
<channel>
<item><title>ProxyFallback</title><link>https://example.com/4</link>
<pubDate>Wed, 04 Jan 2024 00:00:00 GMT</pubDate></item>
</channel>
</rss>"""

        def side_effect(url: str, **kwargs: Any) -> MockResponse:
            if "r.jina.ai" in url:
                return MockResponse(content=rss_content)
            raise Exception("Direct fail")

        mock_session.get.side_effect = side_effect
        fetcher = FeedFetcher(session=mock_session)
        articles = fetcher.fetch("https://example.com/feed")
        assert articles is not None
        assert articles[0].title == "ProxyFallback"
        assert mock_session.get.call_count == 2

    def test_fetch_all_strategies_fail(self) -> None:
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Always fail")
        with patch.object(FeedFetcher, "_fetch_feedparser_direct", return_value=None):
            fetcher = FeedFetcher(session=mock_session)
            articles = fetcher.fetch("https://example.com/feed")
        assert articles is None

    def test_fetch_direct_success_logs(self) -> None:
        mock_session = MagicMock()
        rss_content = b"""<?xml version="1.0"?>
<rss version="2.0">
<channel>
<item><title>DirectLog</title><link>https://example.com/1</link><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item>
</channel>
</rss>"""
        mock_session.get.return_value = MockResponse(content=rss_content)
        fetcher = FeedFetcher(session=mock_session)
        articles = fetcher.fetch("https://example.com/feed")
        assert articles is not None
        assert articles[0].title == "DirectLog"

    def test_fetch_proxy_success_logs(self) -> None:
        mock_session = MagicMock()
        rss_content = b"""<?xml version="1.0"?>
<rss version="2.0">
<channel>
<item><title>ProxyLog</title><link>https://example.com/2</link><pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate></item>
</channel>
</rss>"""

        def side_effect(url: str, **kwargs: Any) -> MockResponse:
            if "r.jina.ai" in url:
                return MockResponse(content=rss_content)
            raise Exception("Direct fail")

        mock_session.get.side_effect = side_effect
        fetcher = FeedFetcher(session=mock_session)
        articles = fetcher.fetch("https://example.com/feed")
        assert articles is not None
        assert articles[0].title == "ProxyLog"

    def test_fetch_feedparser_success_logs(self) -> None:
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Always fail")
        with patch.object(
            FeedFetcher, "_fetch_feedparser_direct",
            return_value=[Article(title="FPLog", link="https://example.com/3", date="2024-01-03")],
        ):
            fetcher = FeedFetcher(session=mock_session)
            articles = fetcher.fetch("https://example.com/feed")
        assert articles is not None
        assert articles[0].title == "FPLog"

    def test_session_injection(self) -> None:
        mock_session = MagicMock()
        fetcher = FeedFetcher(session=mock_session)
        assert fetcher.session is mock_session
