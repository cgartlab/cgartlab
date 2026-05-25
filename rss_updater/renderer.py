from __future__ import annotations

import re
from datetime import UTC, datetime

from rss_updater.models import Article


class MarkdownRenderer:
    @staticmethod
    def _escape_markdown(text: str) -> str:
        chars_to_escape = r"([\\`*_{}[\]()#+\-.!|])"
        return re.sub(chars_to_escape, r"\\\1", text)

    def render_section(
        self,
        articles: list[Article],
        feed_name: str = "",
        max_posts: int = 5,
    ) -> str:
        _ = feed_name  # unused; format uses a static heading
        lines: list[str] = ["## 📝 Latest Blog Posts / 最新博客文章", ""]
        now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines.append(f"*Last Updated: {now}*")
        lines.append("")

        for i, article in enumerate(articles[:max_posts], start=1):
            title = self._escape_markdown(article.title) if article.title else "无标题"
            link = article.link or ""
            date = article.date or "未知日期"

            lines.append(f"**{i}.** [{title}]({link}) - *{date}*")
            lines.append("")

        return "\n".join(lines)

    def update_content(
        self,
        content: str,
        new_section: str,
        section_marker: str,
    ) -> str:
        start_marker = f"<!-- {section_marker}_START -->"
        end_marker = f"<!-- {section_marker}_END -->"

        pattern = re.compile(
            re.escape(start_marker) + r".*?" + re.escape(end_marker),
            re.DOTALL,
        )
        replacement = f"{start_marker}\n{new_section}{end_marker}"

        if pattern.search(content):
            return pattern.sub(replacement, content)

        lines = content.splitlines()
        lines.append("")
        lines.append(start_marker)
        lines.append(new_section.rstrip("\n"))
        lines.append(end_marker)
        return "\n".join(lines) + "\n"
