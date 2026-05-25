from __future__ import annotations

import contextlib
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from rss_updater.detector import ContentChangeDetector
from rss_updater.fetcher import FeedFetcher
from rss_updater.history import HistoryManager
from rss_updater.models import AppConfig, Article, CheckResult, FeedConfig
from rss_updater.notifier import send_notifications
from rss_updater.renderer import MarkdownRenderer

logger = logging.getLogger("rss_updater.updater")


class RSSUpdater:
    def __init__(
        self,
        config: AppConfig,
        check_mode: bool = False,
        force: bool = False,
    ) -> None:
        self.config = config
        self.check_mode = check_mode
        self.force = force
        self.fetcher = FeedFetcher()
        self.detector = ContentChangeDetector()
        self.renderer = MarkdownRenderer()
        self.history = HistoryManager(Path(config.settings.history_dir))

    def _fetch_feed(self, feed: FeedConfig) -> list[Article] | None:
        logger.info("Fetching feed: %s", feed.name)
        articles = self.fetcher.fetch(feed.url, timeout=self.config.settings.timeout_seconds)
        if articles is None:
            logger.error("Failed to fetch feed: %s", feed.name)
        else:
            logger.info("Fetched %d articles from %s", len(articles), feed.name)
        return articles

    def _process_feed(self, feed: FeedConfig) -> CheckResult:
        articles = self._fetch_feed(feed)
        timestamp = datetime.now(UTC).isoformat()

        if articles is None:
            return CheckResult(
                status="error",
                timestamp=timestamp,
                feed_name=feed.name,
                articles_count=0,
                new_articles=[],
                error_message="Failed to fetch feed",
            )

        if self.force:
            logger.info("Force mode: skipping change detection for %s", feed.name)
            new_articles = list(articles)
            current_hash = self.detector.compute_hash(articles)
            self.history.set_last_content_hash(feed.name, current_hash)
            guids = {self.detector._article_guid(a) for a in articles}
            self.history.add_known_guids(feed.name, guids)
            return CheckResult(
                status="success",
                timestamp=timestamp,
                feed_name=feed.name,
                articles_count=len(articles),
                new_articles=new_articles,
                articles=articles,
                content_hash=current_hash,
            )

        changed, new_articles, current_hash = self.detector.detect_changes(feed.name, articles, self.history)

        if changed:
            self.history.set_last_content_hash(feed.name, current_hash)
            guids = {self.detector._article_guid(a) for a in articles}
            self.history.add_known_guids(feed.name, guids)
            status = "success"
        else:
            status = "no_change"
            new_articles = []

        return CheckResult(
            status=status,
            timestamp=timestamp,
            feed_name=feed.name,
            articles_count=len(articles),
            new_articles=new_articles,
            articles=articles,
            content_hash=current_hash,
        )

    def update_readme(self, readme_path: str = "README.md") -> tuple[bool, list[CheckResult]]:
        readme_file = Path(readme_path)
        if not readme_file.exists():
            logger.error("README file not found: %s", readme_path)
            return False, []

        content = readme_file.read_text(encoding="utf-8")
        results: list[CheckResult] = []
        any_new_content = False

        for feed in self.config.feeds:
            if not feed.enabled:
                logger.info("Feed disabled, skipping: %s", feed.name)
                continue
            result = self._process_feed(feed)
            results.append(result)
            self.history.add_check_result(result)

            if result.status == "success" and result.new_articles:
                any_new_content = True
                if not self.check_mode:
                    section = self.renderer.render_section(result.articles, feed.name, feed.max_posts)
                    content = self.renderer.update_content(content, section, feed.section_marker)

                send_notifications(self.config.notifications, feed.name, result.new_articles)

        if any_new_content:
            print("NEW_CONTENT_DETECTED=true")
        else:
            print("NEW_CONTENT_DETECTED=false")

        if self.check_mode:
            logger.info("Check mode: not writing to %s", readme_path)
            return any_new_content, results

        if any_new_content:
            self._atomic_write(readme_file, content)
            print("CONTENT_UPDATED=true")
            logger.info("README updated: %s", readme_path)
        else:
            print("CONTENT_UPDATED=false")

        return any_new_content, results

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, path)
        except Exception:
            logger.exception("Failed to write %s", path)
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)
            raise

    def run(self) -> int:
        try:
            updated, results = self.update_readme()
            errors = [r for r in results if r.status == "error"]
            if errors:
                logger.error("Completed with %d errors", len(errors))
                return 1
            return 0
        except Exception:
            logger.exception("Updater run failed")
            return 1
