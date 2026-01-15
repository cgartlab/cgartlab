#!/usr/bin/env python3
"""
自动获取博客最新文章的脚本（修复版）
支持RSS和Atom订阅源，通过 requests 拉取并设置 User-Agent，处理时间解析、去重、排序，并生成双语 Markdown 列表。
"""

import requests
import feedparser
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Optional

def _parse_entry_date(entry) -> Optional[datetime]:
    """尝试从 entry 中解析时间，优先使用 published_parsed/updated_parsed（time tuple），否则返回 None。"""
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        try:
            return datetime.fromtimestamp(time.mktime(parsed))
        except Exception:
            return None
    # 尝试解析字符串字段（不使用外部依赖以避免额外安装）
    # 如果 entry 中含有 published 或 updated 字符串，直接返回 None 并保留原始字符串
    return None

def fetch_blog_posts(feed_url: str, max_posts: int = 5, timeout: int = 10) -> List[Dict]:
    """
    从RSS/Atom订阅源获取最新文章，使用 requests 获取内容并传给 feedparser。

    Args:
        feed_url: 博客订阅源URL
        max_posts: 每个订阅源最多抓取的文章数
        timeout: requests 请求超时时间（秒）

    Returns:
        文章列表，包含字段 title, link, published (str), published_dt (Optional[datetime]), summary
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; cgartlab-fetch/1.0)"}

    try:
        resp = requests.get(feed_url, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        print(f"[fetch_blog_posts] 请求订阅源失败 {feed_url}: {e}")
        return []

    try:
        feed = feedparser.parse(resp.content)
    except Exception as e:
        print(f"[fetch_blog_posts] 解析订阅源失败 {feed_url}: {e}")
        return []

    posts: List[Dict] = []

    for entry in feed.entries[:max_posts]:
        title = entry.get("title", "(no title)")
        link = entry.get("link", "")
        # 优先尝试解析时间为 datetime 对象
        published_dt = _parse_entry_date(entry)
        if published_dt:
            published_str = published_dt.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # 回退到字符串字段，如果都没有则为空字符串
            published_str = entry.get("published") or entry.get("updated") or ""

        summary = entry.get("summary") or entry.get("description") or ""

        posts.append({
            "title": title,
            "link": link,
            "published": published_str,
            "published_dt": published_dt,
            "summary": summary,
        })

    return posts

def generate_markdown(posts: List[Dict]) -> str:
    """
    生成Markdown格式的文章列表（中英文双语，简洁版）

    Args:
        posts: 文章列表（会读取 title/link/published）

    Returns:
        Markdown格式的内容
    """
    if not posts:
        return (
            "## 📝 Latest Blog Posts / 最新博客文章\n\n"
            "> Temporarily unable to fetch latest posts. Please try again later.\n\n"
            "> 暂时无法获取最新文章，请稍后重试\n"
        )

    markdown = "## 📝 Latest Blog Posts / 最新博客文章\n\n"
    markdown += f"*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"

    for i, post in enumerate(posts, 1):
        title = post.get("title", "(no title)")
        link = post.get("link", "")
        published = post.get("published", "")
        markdown += f"**{i}.** [{title}]({link}) - *{published}*\n\n"

    return markdown

def main():
    """主函数"""
    # 配置文件相对仓库根目录
    config_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "blog_config.json"))
    blog_feeds: List[str] = []

    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                # 支持两种格式：列表 of strings 或 列表 of objects with url
                raw = config.get("blog_feeds", [])
                if isinstance(raw, list):
                    for item in raw:
                        if isinstance(item, str):
                            blog_feeds.append(item)
                        elif isinstance(item, dict) and "url" in item:
                            blog_feeds.append(item["url"])
        except Exception as e:
            print(f"[main] 读取配置文件失败 {config_file}: {e}")

    # 如果没有配置订阅源，保留为空，让后面使用示例条目
    all_posts: List[Dict] = []

    MAX_POSTS_PER_FEED = int(os.environ.get("MAX_POSTS_PER_FEED", "5"))
    MAX_TOTAL_POSTS = int(os.environ.get("MAX_TOTAL_POSTS", "8"))

    # 尝试从多个订阅源获取文章
    for feed_url in blog_feeds:
        feed_url = (feed_url or "").strip()
        if not feed_url:
            continue
        posts = fetch_blog_posts(feed_url, max_posts=MAX_POSTS_PER_FEED)
        all_posts.extend(posts)

    # 如果没有配置订阅源或抓取失败，使用示例数据
    if not all_posts:
        all_posts = [
            {
                "title": "Example Article - Configure Your Blog Feed",
                "link": "https://github.com/cgartlab/cgartlab",
                "published": datetime.now().strftime("%Y-%m-%d"),
                "published_dt": datetime.now(),
                "summary": "Please edit the blog_config.json file to add your blog feed URL",
            }
        ]

    # 去重（根据 link）并按时间降序排序
    unique: Dict[str, Dict] = {}
    for p in all_posts:
        key = p.get("link") or p.get("title")
        if key in unique:
            # 如果已有条目，选择时间更靠近现在的条目
            existing = unique[key]
            # 比较 published_dt，None视为更旧
            a = existing.get("published_dt")
            b = p.get("published_dt")
            if b and (not a or b > a):
                unique[key] = p
        else:
            unique[key] = p

    posts_list = list(unique.values())

    def _sort_key(item):
        dt = item.get("published_dt")
        if dt:
            return dt
        # 尝试从字符串解析简单的 YYYY-MM-DD 或 YYYY-MM-DD HH:MM:SS
        s = item.get("published", "")
        try:
            if len(s) >= 10:
                # 仅尝试常见格式，不引入额外包
                fmt = "%Y-%m-%d %H:%M:%S" if len(s) > 10 else "%Y-%m-%d"
                return datetime.strptime(s[: len(fmt)], fmt)
        except Exception:
            pass
        return datetime(1970, 1, 1)

    posts_list.sort(key=_sort_key, reverse=True)

    # 限制总数
    posts_list = posts_list[:MAX_TOTAL_POSTS]

    # 生成Markdown内容
    markdown_content = generate_markdown(posts_list)

    # 保存到文件
    output_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "BLOG_POSTS.md"))
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print("博客文章列表已更新 ->", output_file)
    except Exception as e:
        print(f"[main] 写入文件失败 {output_file}: {e}")

if __name__ == "__main__":
    main()