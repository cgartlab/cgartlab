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
            # 使用更接近真实浏览器的请求头，优先通过 requests 获取内容
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/116.0.0.0 Safari/537.36'
                ),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
            }

            # 添加 Referer，某些站点会检查来源
            try:
                parsed = urlparse(feed_url)
                if parsed.scheme and parsed.netloc:
                    headers['Referer'] = f"{parsed.scheme}://{parsed.netloc}/"
            except Exception:
                pass

            session = requests.Session()
            session.headers.update(headers)

            # 简单重试机制；在 CI 环境（如 GitHub Actions）默认更快回退到代理
            import time
            last_exc = None
            feed = None


            in_ci = os.environ.get('GITHUB_ACTIONS', '').lower() == 'true'
            force_proxy = os.environ.get('RSS_FORCE_PROXY', '').lower() in ('1', 'true', 'yes')

            # 在 CI（如 GitHub Actions）环境里，许多站点会屏蔽公共云/CI IP，优先使用代理服务以提高成功率
            proxy_mode = in_ci or force_proxy
            if proxy_mode:
                try:
                    normalized = feed_url.split('://', 1)[1]
                    proxy_url = f"https://r.jina.ai/http://{normalized}"
                    print(f"提示: 在 CI/强制代理模式下，尝试通过代理获取: {proxy_url}")
                    resp = session.get(proxy_url, timeout=30)
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.content)
                    if getattr(feed, 'entries', None):
                        print("提示: 通过代理成功获取 RSS 条目")
                    else:
                        print("警告: 代理返回但未解析出条目，回退到直连请求")
                except Exception as proxy_exc:
                    print(f"警告: 代理请求失败 ({proxy_exc})，将回退到直连请求")

            # 如果代理没有成功或不是代理模式，则尝试直连请求（带重试）
            if not getattr(feed, 'entries', None):
                # 如果在 CI，但未强制代理，则缩短重试次数以尽早发现问题
                attempts = 1 if in_ci and not force_proxy else 3
                for attempt in range(attempts):
                    try:
                        response = session.get(feed_url, timeout=30)
                        # 明确处理 403
                        if response.status_code == 403:
                            raise requests.exceptions.HTTPError(f"403 Client Error: Forbidden for url: {feed_url}")
                        response.raise_for_status()
                        feed = feedparser.parse(response.content)

                        # 如果成功解析且有 entries，结束重试
                        if getattr(feed, 'entries', None):
                            break

                        # 有时候服务器返回 HTML 页面或重定向，尝试 feedparser 直接解析 URL
                        feed = feedparser.parse(feed_url)
                        if getattr(feed, 'entries', None):
                            break

                    except requests.exceptions.RequestException as req_exc:
                        last_exc = req_exc
                        wait = 2 * (attempt + 1)
                        print(f"警告: 请求 {feed_url} 第 {attempt + 1} 次失败 ({req_exc})，等待 {wait}s 后重试")
                        time.sleep(wait)
                        continue

                # 若直连也失败，则再尝试一次代理（双重保险）
                if not getattr(feed, 'entries', None):
                    try:
                        normalized = feed_url.split('://', 1)[1]
                        proxy_url = f"https://r.jina.ai/http://{normalized}"
                        print(f"警告: 直连失败，最后尝试通过代理获取: {proxy_url}")
                        response = session.get(proxy_url, timeout=30)
                        response.raise_for_status()
                        feed = feedparser.parse(response.content)
                    except Exception as proxy_exc:
                        print(f"错误: 通过代理获取失败 ({proxy_exc})，最后一次请求错误: {last_exc}")
                        # 最后回退到 feedparser 直接解析（可能不同的底层实现）
                        feed = feedparser.parse(feed_url)

            if not getattr(feed, 'entries', None):
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
            # 检查文件是否存在
            if not os.path.exists(readme_path):
                print(f"错误: README文件不存在 - {readme_path}")
                return False
            
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
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
                    print(f"✅ 成功更新 {feed['name']} 的内容区域")
                else:
                    print(f"警告: 未找到标记 {feed['section_marker']}，将添加到文件末尾")
                    updated_content += f"\n\n{replacement}"
            
            # 检查内容是否真的发生了变化
            if original_content == updated_content:
                print("⚠️ README内容没有变化，跳过写入")
                return False
            
            # 写入更新后的内容
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            print("✅ README.md 更新成功!")
            return True
            
        except Exception as e:
            print(f"错误: 更新README失败 - {e}")
            import traceback
            traceback.print_exc()
            return False

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
    success = updater.update_readme()
    
    if success:
        print("✅ 更新完成!")
        sys.exit(0)
    else:
        print("⚠️ 更新失败或没有变化!")
        sys.exit(1)

if __name__ == "__main__":
    main()