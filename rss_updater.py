#!/usr/bin/env python3
"""
RSS订阅更新器
自动从RSS订阅源获取最新文章并更新README.md文件
"""

import feedparser
import re
from datetime import datetime
import os
import sys
from urllib.parse import urlparse
import requests
from typing import List, Dict, Optional

class RSSUpdater:
    def __init__(self, config_file: str = "rss_config.json"):
        self.config_file = config_file
        self.rss_feeds = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载RSS配置"""
        import json
        
        default_config = {
            "feeds": [
                {
                    "name": "CGArtLab Blog",
                    "url": "https://cgartlab.com/rss.xml",
                    "section_marker": "BLOG_POSTS_START",
                    "max_posts": 5
                }
            ]
        }
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 如果配置文件不存在，创建默认配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
    
    def fetch_rss_feed(self, feed_url: str) -> Optional[List[Dict]]:
        """获取RSS订阅内容"""
        try:
            # 设置请求头，避免被阻止
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # 尝试直接解析
            feed = feedparser.parse(feed_url)
            
            # 如果解析失败，尝试使用requests获取
            if feed.bozo and hasattr(feed.bozo_exception, 'getMessage'):
                response = requests.get(feed_url, headers=headers, timeout=30)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
            
            if not feed.entries:
                print(f"警告: 无法从 {feed_url} 获取文章")
                return None
            
            articles = []
            for entry in feed.entries:
                # 处理日期格式
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    date_obj = datetime(*entry.published_parsed[:6])
                    date_str = date_obj.strftime('%Y-%m-%d')
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    date_obj = datetime(*entry.updated_parsed[:6])
                    date_str = date_obj.strftime('%Y-%m-%d')
                else:
                    date_str = "未知日期"
                
                articles.append({
                    'title': entry.title,
                    'link': entry.link,
                    'date': date_str,
                    'description': getattr(entry, 'description', '')
                })
            
            return articles
            
        except Exception as e:
            print(f"错误: 获取RSS订阅失败 - {e}")
            return None
    
    def generate_markdown_section(self, articles: List[Dict], feed_name: str, max_posts: int = 5) -> str:
        """生成Markdown格式的文章列表"""
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        markdown = f"""
## 📝 Latest Blog Posts / 最新博客文章

*Last Updated: {current_time}*

"""
        
        for i, article in enumerate(articles[:max_posts], 1):
            markdown += f"**{i}.** [{article['title']}]({article['link']}) - *{article['date']}*\n\n"
        
        return markdown
    
    def update_readme(self, readme_path: str = "README.md"):
        """更新README文件"""
        try:
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            updated_content = content
            
            for feed in self.rss_feeds["feeds"]:
                articles = self.fetch_rss_feed(feed["url"])
                if not articles:
                    print(f"跳过 {feed['name']} - 无法获取文章")
                    continue
                
                new_section = self.generate_markdown_section(
                    articles, 
                    feed["name"], 
                    feed.get("max_posts", 5)
                )
                
                # 查找并替换对应的部分
                start_marker = f"<!-- {feed['section_marker']} -->"
                end_marker = f"<!-- {feed['section_marker'].replace('START', 'END')} -->"
                
                pattern = re.compile(
                    re.escape(start_marker) + r'.*?' + re.escape(end_marker), 
                    re.DOTALL
                )
                
                replacement = f"{start_marker}\n{new_section}\n{end_marker}"
                
                if pattern.search(updated_content):
                    updated_content = pattern.sub(replacement, updated_content)
                else:
                    print(f"警告: 未找到标记 {feed['section_marker']}，将添加到文件末尾")
                    updated_content += f"\n\n{replacement}"
            
            # 写入更新后的内容
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print("✅ README.md 更新成功!")
            
        except Exception as e:
            print(f"错误: 更新README失败 - {e}")
            sys.exit(1)

def main():
    """主函数"""
    # 设置编码以确保在Windows下正常显示emoji
    import sys
    import io
    
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    updater = RSSUpdater()
    
    print("开始更新RSS订阅...")
    
    # 显示配置信息
    print(f"加载了 {len(updater.rss_feeds['feeds'])} 个RSS订阅源:")
    for feed in updater.rss_feeds["feeds"]:
        print(f"  - {feed['name']}: {feed['url']}")
    
    # 更新README
    updater.update_readme()
    
    print("更新完成!")

if __name__ == "__main__":
    main()