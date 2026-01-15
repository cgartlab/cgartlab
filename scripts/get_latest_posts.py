#!/usr/bin/env python3
"""
简化版：获取最新博客文章列表（改进版）
- 更详细的日志
- 遇到错误时返回非0退出码（便于 CI 识别失败）
- 当没有更新时明确输出并返回0
"""

import requests
import feedparser
import re
import sys
from datetime import datetime


def fetch_latest_posts(feed_url: str, max_posts: int = 5) -> str:
    """从RSS源获取最新文章，返回Markdown格式（失败时抛出异常）"""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; cgartlab/1.0)",
    }
    
    resp = requests.get(feed_url, headers=headers, timeout=15)
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)

    entries = feed.entries or []
    print(f"[fetch_latest_posts] 找到 {len(entries)} 条条目（取前 {max_posts} 条）")

    if not entries:
        return ""

    posts = []
    for entry in entries[:max_posts]:
        title = entry.get('title', '无标题')
        link = entry.get('link', '#')
        pub_time = entry.get('published_parsed') or entry.get('updated_parsed')
        if pub_time:
            pub_str = datetime(*pub_time[:6]).strftime('%Y-%m-%d %H:%M:%S')
        else:
            pub_str = '未知时间'
        posts.append(f"**{len(posts) + 1}.** [{title}]({link}) - *{pub_str}*")

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    content = f"## 📝 Latest Blog Posts / 最新博客文章\n\n"
    content += f"*Last Updated: {now}*\n\n"
    content += "\n\n".join(posts) + "\n\n"
    return content


def update_readme(feed_url: str = None) -> int:
    """更新README.md中的博客列表，返回退出码：0=成功/无变更, 1=失败, 2=已更新"""
    if feed_url is None:
        feed_url = "https://cgartlab.com/rss.xml"

    try:
        blog_content = fetch_latest_posts(feed_url)
    except Exception as e:
        print(f"❌ 拉取订阅源失败: {e}")
        return 1

    if not blog_content:
        print("❗ 未找到任何文章（订阅源可能为空或解析失败）")
        return 1

    # 读取 README
    with open('README.md', 'r', encoding='utf-8') as f:
        readme = f.read()

    pattern = r'<!-- BLOG_POSTS_START -->.*?<!-- BLOG_POSTS_END -->'
    replacement = f'<!-- BLOG_POSTS_START -->\n{blog_content}<!-- BLOG_POSTS_END -->'
    updated = re.sub(pattern, replacement, readme, flags=re.DOTALL)

    if updated == readme:
        print("ℹ️ README.md 中的博客列表已是最新，无需更新")
        return 0

    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(updated)

    print("✅ README.md 已成功更新")
    return 2


if __name__ == "__main__":
    exit_code = update_readme()
    if exit_code == 0:
        sys.exit(0)
    elif exit_code == 2:
        sys.exit(0)
    else:
        sys.exit(1)
