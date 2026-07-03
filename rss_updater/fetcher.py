from __future__ import annotations

import logging
import time

import feedparser  # type: ignore[import-untyped]
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from rss_updater.models import Article

logger = logging.getLogger("rss_updater.fetcher")


class FeedFetcher:
    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = self._create_session()
        return self._session

    def _build_headers(self, feed_url: str) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": feed_url,
        }

    @staticmethod
    def _parse_date(entry: feedparser.FeedParserDict) -> str:
        parsed = None
        for key in ("published_parsed", "updated_parsed", "created_parsed"):
            parsed = entry.get(key)
            if parsed is not None:
                break
        if parsed is not None:
            try:
                return time.strftime("%Y-%m-%d", parsed)
            except (TypeError, ValueError):
                pass
        return "未知日期"

    def _entry_to_article(self, entry: feedparser.FeedParserDict) -> Article:
        return Article(
            title=entry.get("title", ""),
            link=entry.get("link", ""),
            date=self._parse_date(entry),
            description=entry.get("description", ""),
            author=entry.get("author", ""),
            guid=entry.get("id", entry.get("link", "")),
        )

    def _fetch_direct(
        self,
        session: requests.Session,
        feed_url: str,
        headers: dict[str, str],
        timeout: float,
    ) -> list[Article] | None:
        try:
            response = session.get(feed_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            if parsed.entries:
                return [self._entry_to_article(entry) for entry in parsed.entries]
        except Exception:
            logger.exception("Direct fetch failed for %s", feed_url)
        return None

    def _fetch_via_proxy(
        self,
        session: requests.Session,
        feed_url: str,
        headers: dict[str, str],
        timeout: float,
    ) -> list[Article] | None:
        proxy_url = f"https://r.jina.ai/{feed_url}"
        try:
            response = session.get(proxy_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
            if parsed.entries:
                return [self._entry_to_article(entry) for entry in parsed.entries]
        except Exception:
            logger.exception("Proxy fetch failed for %s", feed_url)
        return None

    def _fetch_feedparser_direct(self, feed_url: str) -> list[Article] | None:
        try:
            parsed = feedparser.parse(feed_url)
            if parsed.entries:
                return [self._entry_to_article(entry) for entry in parsed.entries]
        except Exception:
            logger.exception("Feedparser direct fetch failed for %s", feed_url)
        return None

    def fetch(
        self,
        feed_url: str,
        timeout: float = 15.0,
    ) -> list[Article] | None:
        headers = self._build_headers(feed_url)

        articles = self._fetch_direct(self.session, feed_url, headers, timeout)
        if articles is not None:
            logger.info("Direct fetch succeeded for %s", feed_url)
            return articles

        articles = self._fetch_via_proxy(self.session, feed_url, headers, timeout)
        if articles is not None:
            logger.info("Proxy fetch succeeded for %s", feed_url)
            return articles

        articles = self._fetch_feedparser_direct(feed_url)
        if articles is not None:
            logger.info("Feedparser direct fetch succeeded for %s", feed_url)
            return articles

        logger.error("All fetch strategies failed for %s", feed_url)
        return None
