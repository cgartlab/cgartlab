from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

from rss_updater.models import Article
from rss_updater.renderer import MarkdownRenderer


class TestMarkdownRenderer:
    def test_escape_markdown(self) -> None:
        text = "Hello *world* [link](url) #tag"
        expected = r"Hello \*world\* \[link\]\(url\) \#tag"
        assert MarkdownRenderer._escape_markdown(text) == expected

    def test_render_section_basic(self) -> None:
        renderer = MarkdownRenderer()
        articles = [
            Article(title="Title 1", link="https://example.com/1", date="2024-01-01"),
            Article(title="Title 2", link="https://example.com/2", date="2024-01-02"),
        ]
        with patch("rss_updater.renderer.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = renderer.render_section(articles, "Test Feed", max_posts=5)

        assert "## Test Feed" in result
        assert "*Last Updated: 2024-06-15 12:00:00 UTC*" in result
        assert "[Title 1](https://example.com/1) - 2024-01-01" in result
        assert "[Title 2](https://example.com/2) - 2024-01-02" in result

    def test_render_section_with_description(self) -> None:
        renderer = MarkdownRenderer()
        articles = [
            Article(
                title="Desc Article",
                link="https://example.com/d",
                date="2024-03-01",
                description="A description",
            ),
        ]
        with patch("rss_updater.renderer.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = renderer.render_section(articles, "Feed", max_posts=5)

        assert "  > A description" in result

    def test_render_section_max_posts(self) -> None:
        renderer = MarkdownRenderer()
        articles = [Article(title=f"Title {i}", link=f"https://example.com/{i}", date="2024-01-01") for i in range(10)]
        result = renderer.render_section(articles, "Feed", max_posts=3)
        assert result.count("https://example.com/") == 3

    def test_render_section_escapes_title(self) -> None:
        renderer = MarkdownRenderer()
        articles = [
            Article(title="Title *bold*", link="https://example.com/1", date="2024-01-01"),
        ]
        result = renderer.render_section(articles, "Feed", max_posts=5)
        assert r"Title \*bold\*" in result

    def test_render_section_empty_title(self) -> None:
        renderer = MarkdownRenderer()
        articles = [
            Article(title="", link="https://example.com/1", date="2024-01-01"),
        ]
        result = renderer.render_section(articles, "Feed", max_posts=5)
        assert "[无标题]" in result

    def test_update_content_replace_existing(self) -> None:
        renderer = MarkdownRenderer()
        content = """# README

<!-- FEED_START -->
Old content
<!-- FEED_END -->

Footer
"""
        new_section = "## New Feed\n\n- [Item](https://example.com)\n"
        result = renderer.update_content(content, new_section, "FEED")

        assert "Old content" not in result
        assert "## New Feed" in result
        assert "<!-- FEED_START -->" in result
        assert "<!-- FEED_END -->" in result

    def test_update_content_append_new(self) -> None:
        renderer = MarkdownRenderer()
        content = "# README\n\nFooter\n"
        new_section = "## New Feed\n\n- [Item](https://example.com)\n"
        result = renderer.update_content(content, new_section, "FEED")

        assert "## New Feed" in result
        assert "<!-- FEED_START -->" in result
        assert "<!-- FEED_END -->" in result
        assert "# README" in result

    def test_update_content_multiline_section(self) -> None:
        renderer = MarkdownRenderer()
        content = """# README

<!-- FEED_START -->
Line1
Line2
<!-- FEED_END -->
"""
        new_section = "Updated\n"
        result = renderer.update_content(content, new_section, "FEED")
        assert "Line1" not in result
        assert "Updated" in result
