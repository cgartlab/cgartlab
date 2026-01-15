#!/usr/bin/env python3
"""
简化版：获取最新博客文章列表
"""

import requests
import feedparser
import re
from datetime import datetime


def fetch_latest_posts(feed_url: str, max_posts: int = 5) -> str:
    """从RSS源获取最新文章，返回Markdown格式"""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; cgartlab/1.0)",
    }
    
    try:
        resp = requests.get(feed_url, headers=headers, timeout=10)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        
        if not feed.entries:
            return "未找到文章\n"
        
        # 提取最新的N篇文章
        posts = []
        for entry in feed.entries[:max_posts]:
            title = entry.get('title', '无标题')
            link = entry.get('link', '#')
            # 优先使用 published_parsed，其次 updated_parsed
            pub_time = entry.get('published_parsed') or entry.get('updated_parsed')
            if pub_time:
                pub_str = datetime(*pub_time[:6]).strftime('%Y-%m-%d %H:%M:%S')
            else:
                pub_str = '未知时间'
            
            posts.append(f"**{len(posts) + 1}.** [{title}]({link}) - *{pub_str}*")
        
        # 构建Markdown内容
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        content = f"## 📝 Latest Blog Posts / 最新博客文章\n\n"
        content += f"*Last Updated: {now}*\n\n"
        content += "\n\n".join(posts) + "\n\n"
        
        return content
        
    except Exception as e:
        print(f"获取失败: {e}")
        return ""


def update_readme():
    """更新README.md中的博客列表"""
    feed_url = "https://cgartlab.com/rss.xml"
    blog_content = fetch_latest_posts(feed_url)
    
    if not blog_content:
        print("❌ 获取博客文章失败")
        return False
    
    # 读取README
    with open('README.md', 'r', encoding='utf-8') as f:
        readme = f.read()
    
    # 替换博客部分
    pattern = r'<!-- BLOG_POSTS_START -->.*?<!-- BLOG_POSTS_END -->'
    replacement = f'<!-- BLOG_POSTS_START -->\n{blog_content}<!-- BLOG_POSTS_END -->'
    
    updated = re.sub(pattern, replacement, readme, flags=re.DOTALL)
    
    # 写回README
    with open('README.md', 'w', encoding='utf-8') as f:
        f.write(updated)
    
    print("✅ README.md 已更新")
    return True


if __name__ == "__main__":
    update_readme()
