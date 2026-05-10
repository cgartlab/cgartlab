from __future__ import annotations

import hashlib
import json
import logging

from rss_updater.history import HistoryManager
from rss_updater.models import Article

logger = logging.getLogger("rss_updater.detector")


class ContentChangeDetector:
    @staticmethod
    def compute_hash(articles: list[Article]) -> str:
        data = json.dumps(
            [a.model_dump() for a in articles],
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def _identify_new_articles(
        self,
        feed_name: str,
        current_articles: list[Article],
        history: HistoryManager,
    ) -> list[Article]:
        last_hash = history.get_last_content_hash(feed_name)
        if last_hash is None:
            logger.info("No previous hash for %s, treating all as new", feed_name)
            return list(current_articles)

        new_articles: list[Article] = []
        for article in current_articles:
            article_hash = hashlib.sha256(
                article.model_dump_json().encode("utf-8")
            ).hexdigest()
            if article_hash != last_hash:
                new_articles.append(article)

        return new_articles

    def detect_changes(
        self,
        feed_name: str,
        current_articles: list[Article],
        history: HistoryManager,
    ) -> tuple[bool, list[Article], str]:
        current_hash = self.compute_hash(current_articles)
        last_hash = history.get_last_content_hash(feed_name)

        if last_hash == current_hash:
            logger.info("No changes detected for %s", feed_name)
            return False, [], current_hash

        new_articles = self._identify_new_articles(feed_name, current_articles, history)
        logger.info(
            "Changes detected for %s: %d new articles",
            feed_name,
            len(new_articles),
        )
        return True, new_articles, current_hash
