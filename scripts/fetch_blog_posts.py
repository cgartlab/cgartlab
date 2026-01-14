#!/usr/bin/env python3
"""
自动获取博客最新文章的脚本
支持RSS和Atom订阅源
"""

import requests
import feedparser
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional


def fetch_blog_posts(feed_url: str, max_posts: int = 5) -> List[Dict]:
    """
    从RSS/Atom订阅源获取最新文章
    
    Args:
        feed_url: 博客订阅源URL
        max_posts: 最大文章数量
    
    Returns:
        文章列表
    """
    try:
        # 解析订阅源
        feed = feedparser.parse(feed_url)
        
        posts = []
        for entry in feed.entries[:max_posts]:
            post = {
                'title': entry.title,
                'link': entry.link,
                'published': entry.get('published', entry.get('updated', '')),
                'summary': entry.get('summary', entry.get('description', ''))
            }
            posts.append(post)
        
        return posts
    except Exception as e:
        print(f"获取博客文章失败: {e}")
        return []


def generate_markdown(posts: List[Dict]) -> str:
    """
    生成Markdown格式的文章列表（中英文双语，简洁版）
    
    Args:
        posts: 文章列表
    
    Returns:
        Markdown格式的内容
    """
    if not posts:
        return "## 📝 Latest Blog Posts / 最新博客文章\n\n> Temporarily unable to fetch latest posts. Please try again later.\n\n> 暂时无法获取最新文章，请稍后重试\n"
    
    markdown = "## 📝 Latest Blog Posts / 最新博客文章\n\n"
    markdown += f"*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
    
    for i, post in enumerate(posts, 1):
        markdown += f"**{i}.** [{post['title']}]({post['link']}) - *{post['published']}*\n\n"
    
    return markdown


def main():
    """主函数"""
    # 尝试从配置文件读取订阅源
    config_file = os.path.join(os.path.dirname(__file__), '..', 'blog_config.json')
    blog_feeds = []
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                blog_feeds = [feed['url'] for feed in config.get('blog_feeds', []) if 'url' in feed]
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    
    # 如果没有配置文件或配置为空，使用示例数据
    if not blog_feeds:
        blog_feeds = []
    
    all_posts = []
    
    # 尝试从多个订阅源获取文章
    for feed_url in blog_feeds:
        if feed_url.strip():  # 跳过空URL
            posts = fetch_blog_posts(feed_url)
            all_posts.extend(posts)
    
    # 如果没有配置订阅源，使用示例数据
    if not all_posts:
        all_posts = [
            {
                'title': 'Example Article - Configure Your Blog Feed',
                'link': 'https://github.com/cgartlab/cgartlab',
                'published': datetime.now().strftime('%Y-%m-%d'),
                'summary': 'Please edit the blog_config.json file to add your blog feed URL'
            }
        ]
    
    # 生成Markdown内容
    markdown_content = generate_markdown(all_posts)
    
    # 保存到文件
    output_file = os.path.join(os.path.dirname(__file__), '..', 'BLOG_POSTS.md')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print("博客文章列表已更新")


if __name__ == "__main__":
    main()