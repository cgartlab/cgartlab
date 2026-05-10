from __future__ import annotations

from unittest.mock import MagicMock

from rss_updater.detector import ContentChangeDetector
from rss_updater.models import Article


class TestContentChangeDetector:
    def test_compute_hash_consistency(self) -> None:
        articles = [
            Article(title="A", link="https://example.com/a", date="2024-01-01"),
            Article(title="B", link="https://example.com/b", date="2024-01-02"),
        ]
        h1 = ContentChangeDetector.compute_hash(articles)
        h2 = ContentChangeDetector.compute_hash(articles)
        assert h1 == h2
        assert len(h1) == 64

    def test_compute_hash_different_order(self) -> None:
        articles1 = [
            Article(title="A", link="https://example.com/a"),
            Article(title="B", link="https://example.com/b"),
        ]
        articles2 = [
            Article(title="B", link="https://example.com/b"),
            Article(title="A", link="https://example.com/a"),
        ]
        h1 = ContentChangeDetector.compute_hash(articles1)
        h2 = ContentChangeDetector.compute_hash(articles2)
        assert h1 != h2

    def test_detect_changes_no_previous_hash(self) -> None:
        detector = ContentChangeDetector()
        mock_history = MagicMock()
        mock_history.get_last_content_hash.return_value = None

        articles = [Article(title="New", link="https://example.com/new", date="2024-01-01")]
        changed, new_articles, current_hash = detector.detect_changes("feed1", articles, mock_history)

        assert changed is True
        assert len(new_articles) == 1
        assert current_hash == detector.compute_hash(articles)

    def test_detect_changes_no_changes(self) -> None:
        detector = ContentChangeDetector()
        articles = [Article(title="Same", link="https://example.com/same", date="2024-01-01")]
        current_hash = detector.compute_hash(articles)

        mock_history = MagicMock()
        mock_history.get_last_content_hash.return_value = current_hash

        changed, new_articles, returned_hash = detector.detect_changes("feed1", articles, mock_history)

        assert changed is False
        assert new_articles == []
        assert returned_hash == current_hash

    def test_detect_changes_with_changes(self) -> None:
        detector = ContentChangeDetector()
        old_articles = [Article(title="Old", link="https://example.com/old", date="2024-01-01")]
        new_articles_list = [
            Article(title="Old", link="https://example.com/old", date="2024-01-01"),
            Article(title="New", link="https://example.com/new", date="2024-01-02"),
        ]
        old_hash = detector.compute_hash(old_articles)

        mock_history = MagicMock()
        mock_history.get_last_content_hash.return_value = old_hash

        changed, new_articles, returned_hash = detector.detect_changes("feed1", new_articles_list, mock_history)

        assert changed is True
        assert len(new_articles) == 2
        assert returned_hash == detector.compute_hash(new_articles_list)

    def test_identify_new_articles_no_history(self) -> None:
        detector = ContentChangeDetector()
        mock_history = MagicMock()
        mock_history.get_last_content_hash.return_value = None

        articles = [Article(title="A", link="https://example.com/a")]
        result = detector._identify_new_articles("feed1", articles, mock_history)
        assert result == articles

    def test_identify_new_articles_with_history(self) -> None:
        detector = ContentChangeDetector()
        article_a = Article(title="A", link="https://example.com/a")
        article_b = Article(title="B", link="https://example.com/b")

        mock_history = MagicMock()
        mock_history.get_last_content_hash.return_value = detector.compute_hash([article_a])

        result = detector._identify_new_articles("feed1", [article_a, article_b], mock_history)
        assert len(result) == 2
