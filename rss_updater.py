#!/usr/bin/env python3
"""
RSS订阅更新器 - 增强版
自动从RSS订阅源获取最新文章并更新README.md文件
支持：内容变更检测、历史记录存储、日志系统、容错处理、通知机制
"""

import feedparser
import re
import json
import hashlib
import logging
import argparse
import sys
import os
import io
from datetime import datetime, timedelta
from urllib.parse import urlparse
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class UpdateStatus(Enum):
    NEW_CONTENT = "new_content"
    UPDATED = "updated"
    NO_CHANGE = "no_change"
    ERROR = "error"


@dataclass
class CheckResult:
    status: UpdateStatus
    timestamp: str
    feed_name: str
    articles_count: int
    new_articles: List[Dict]
    error_message: Optional[str] = None
    content_hash: Optional[str] = None


class RSSLogger:
    def __init__(self, log_dir: str = ".rss_history", log_level: str = "INFO"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("RSSUpdater")
        self.logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        if not self.logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(console_format)
            self.logger.addHandler(console_handler)
            
            file_handler = logging.FileHandler(
                self.log_dir / "rss_updater.log",
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
    
    def info(self, msg: str):
        self.logger.info(msg)
    
    def error(self, msg: str):
        self.logger.error(msg)
    
    def warning(self, msg: str):
        self.logger.warning(msg)
    
    def debug(self, msg: str):
        self.logger.debug(msg)


class HistoryManager:
    def __init__(self, history_dir: str = ".rss_history", logger: Optional[RSSLogger] = None):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger or RSSLogger(history_dir)
        self.history_file = self.history_dir / "check_history.json"
        self.max_history_days = 30
    
    def load_history(self) -> Dict:
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load history: {e}")
        return {"checks": [], "last_content_hash": {}}
    
    def save_history(self, history: Dict):
        try:
            self._cleanup_old_history(history)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save history: {e}")
    
    def _cleanup_old_history(self, history: Dict):
        cutoff_date = (datetime.now() - timedelta(days=self.max_history_days)).isoformat()
        history["checks"] = [
            check for check in history.get("checks", [])
            if check.get("timestamp", "") > cutoff_date
        ]
    
    def get_last_content_hash(self, feed_name: str) -> Optional[str]:
        history = self.load_history()
        return history.get("last_content_hash", {}).get(feed_name)
    
    def set_last_content_hash(self, feed_name: str, content_hash: str):
        history = self.load_history()
        if "last_content_hash" not in history:
            history["last_content_hash"] = {}
        history["last_content_hash"][feed_name] = content_hash
        self.save_history(history)
    
    def add_check_result(self, result: CheckResult):
        history = self.load_history()
        if "checks" not in history:
            history["checks"] = []
        history["checks"].append(asdict(result))
        self.save_history(history)
    
    def get_recent_checks(self, feed_name: str, limit: int = 10) -> List[Dict]:
        history = self.load_history()
        checks = history.get("checks", [])
        return [
            check for check in checks
            if check.get("feed_name") == feed_name
        ][-limit:]


class ContentChangeDetector:
    def __init__(self, history_manager: HistoryManager, logger: Optional[RSSLogger] = None):
        self.history_manager = history_manager
        self.logger = logger or RSSLogger()
    
    def compute_content_hash(self, articles: List[Dict]) -> str:
        content_str = json.dumps(articles, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()
    
    def detect_changes(self, feed_name: str, current_articles: List[Dict]) -> Tuple[bool, List[Dict], str]:
        current_hash = self.compute_content_hash(current_articles)
        last_hash = self.history_manager.get_last_content_hash(feed_name)
        
        if last_hash is None:
            self.logger.info(f"First check for {feed_name}, storing content hash")
            self.history_manager.set_last_content_hash(feed_name, current_hash)
            return True, current_articles, current_hash
        
        if current_hash == last_hash:
            self.logger.debug(f"No content changes detected for {feed_name}")
            return False, [], current_hash
        
        new_articles = self._identify_new_articles(feed_name, current_articles)
        self.logger.info(f"Content changes detected for {feed_name}: {len(new_articles)} new articles")
        
        self.history_manager.set_last_content_hash(feed_name, current_hash)
        return True, new_articles, current_hash
    
    def _identify_new_articles(self, feed_name: str, current_articles: List[Dict]) -> List[Dict]:
        history = self.history_manager.load_history()
        known_links = set()
        
        for check in history.get("checks", []):
            if check.get("feed_name") == feed_name:
                for article in check.get("new_articles", []):
                    known_links.add(article.get("link"))
        
        new_articles = [
            article for article in current_articles
            if article.get("link") not in known_links
        ]
        
        return new_articles


class NotificationManager:
    def __init__(self, config: Dict, logger: Optional[RSSLogger] = None):
        self.config = config
        self.logger = logger or RSSLogger()
        self.notifications_enabled = config.get("notifications", {}).get("enabled", False)
    
    def notify_new_content(self, feed_name: str, new_articles: List[Dict]):
        if not self.notifications_enabled:
            return
        
        notification_config = self.config.get("notifications", {})
        
        webhook_url = notification_config.get("webhook_url")
        if webhook_url:
            self._send_webhook_notification(webhook_url, feed_name, new_articles)
        
        telegram_token = notification_config.get("telegram_token")
        telegram_chat_id = notification_config.get("telegram_chat_id")
        if telegram_token and telegram_chat_id:
            self._send_telegram_notification(telegram_token, telegram_chat_id, feed_name, new_articles)
    
    def _send_webhook_notification(self, webhook_url: str, feed_name: str, new_articles: List[Dict]):
        try:
            payload = {
                "feed_name": feed_name,
                "new_articles_count": len(new_articles),
                "articles": new_articles[:5],
                "timestamp": datetime.now().isoformat()
            }
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                self.logger.info(f"Webhook notification sent successfully")
            else:
                self.logger.warning(f"Webhook notification failed: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {e}")
    
    def _send_telegram_notification(self, token: str, chat_id: str, feed_name: str, new_articles: List[Dict]):
        try:
            message = f"📰 **{feed_name}** 有新文章发布！\n\n"
            for i, article in enumerate(new_articles[:5], 1):
                message += f"{i}. [{article['title']}]({article['link']})\n"
            
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                self.logger.info("Telegram notification sent successfully")
            else:
                self.logger.warning(f"Telegram notification failed: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Failed to send Telegram notification: {e}")


class RSSUpdater:
    def __init__(self, config_file: str = "rss_config.json", check_mode: bool = False):
        self.config_file = config_file
        self.check_mode = check_mode
        self.config = self._load_config()
        
        log_level = self.config.get("settings", {}).get("log_level", "INFO")
        history_dir = self.config.get("settings", {}).get("history_dir", ".rss_history")
        
        self.logger = RSSLogger(history_dir, log_level)
        self.history_manager = HistoryManager(history_dir, self.logger)
        self.change_detector = ContentChangeDetector(self.history_manager, self.logger)
        self.notification_manager = NotificationManager(self.config, self.logger)
        
        self.rss_feeds = self.config.get("feeds", [])
        self.settings = self.config.get("settings", {
            "check_interval_minutes": 60,
            "max_retries": 3,
            "timeout_seconds": 15,
            "history_dir": ".rss_history",
            "log_level": "INFO"
        })
    
    def _load_config(self) -> Dict:
        default_config = {
            "feeds": [
                {
                    "name": "CGArtLab Blog",
                    "url": "https://cgartlab.com/rss.xml",
                    "section_marker": "BLOG_POSTS_START",
                    "max_posts": 5,
                    "enabled": True
                }
            ],
            "settings": {
                "check_interval_minutes": 60,
                "max_retries": 3,
                "timeout_seconds": 15,
                "history_dir": ".rss_history",
                "log_level": "INFO"
            },
            "notifications": {
                "enabled": False,
                "webhook_url": "",
                "telegram_token": "",
                "telegram_chat_id": ""
            }
        }
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if "settings" not in config:
                    config["settings"] = default_config["settings"]
                if "notifications" not in config:
                    config["notifications"] = default_config["notifications"]
                return config
        except FileNotFoundError:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            return default_config
        except json.JSONDecodeError as e:
            print(f"Error parsing config file: {e}")
            return default_config
    
    def _create_session_with_retry(self) -> requests.Session:
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.settings.get("max_retries", 3),
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def fetch_rss_feed(self, feed_url: str) -> Optional[List[Dict]]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/xml,application/rss+xml,text/xml;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        try:
            parsed = urlparse(feed_url)
            if parsed.scheme and parsed.netloc:
                headers['Referer'] = f"{parsed.scheme}://{parsed.netloc}/"
        except Exception:
            pass
        
        session = self._create_session_with_retry()
        timeout = self.settings.get("timeout_seconds", 15)
        
        self.logger.info(f"Fetching RSS feed: {feed_url}")
        
        try:
            response = session.get(feed_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
            
            if getattr(feed, 'entries', None):
                self.logger.info(f"Direct fetch successful, found {len(feed.entries)} entries")
                return self._parse_feed_entries(feed)
            else:
                self.logger.warning("Direct fetch returned no entries, trying proxy...")
        except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout after {timeout}s, trying proxy...")
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"Connection error: {e}, trying proxy...")
        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"HTTP error: {e}, trying proxy...")
        except Exception as e:
            self.logger.warning(f"Direct fetch failed: {e}, trying proxy...")
        
        proxy_url = f"https://r.jina.ai/{feed_url}"
        try:
            self.logger.info(f"Trying proxy: {proxy_url}")
            proxy_response = session.get(proxy_url, headers=headers, timeout=timeout + 5)
            proxy_response.raise_for_status()
            feed = feedparser.parse(proxy_response.content)
            
            if getattr(feed, 'entries', None):
                self.logger.info(f"Proxy fetch successful, found {len(feed.entries)} entries")
                return self._parse_feed_entries(feed)
        except Exception as e:
            self.logger.warning(f"Proxy fetch failed: {e}")
        
        try:
            self.logger.info("Trying feedparser direct parse...")
            feed = feedparser.parse(feed_url)
            if getattr(feed, 'entries', None):
                self.logger.info(f"Feedparser direct parse successful")
                return self._parse_feed_entries(feed)
        except Exception as e:
            self.logger.error(f"Feedparser direct parse failed: {e}")
        
        self.logger.error(f"All fetch methods failed for {feed_url}")
        return None
    
    def _parse_feed_entries(self, feed) -> List[Dict]:
        articles = []
        for entry in feed.entries:
            date_str = "未知日期"
            
            for attr in ['published_parsed', 'updated_parsed', 'created_parsed']:
                if hasattr(entry, attr) and getattr(entry, attr):
                    try:
                        date_obj = datetime(*getattr(entry, attr)[:6])
                        date_str = date_obj.strftime('%Y-%m-%d')
                        break
                    except Exception:
                        pass
            
            articles.append({
                'title': entry.get('title', 'Untitled'),
                'link': entry.get('link', ''),
                'date': date_str,
                'description': entry.get('description', ''),
                'author': entry.get('author', ''),
                'guid': entry.get('guid', entry.get('link', ''))
            })
        
        return articles
    
    def generate_markdown_section(self, articles: List[Dict], feed_name: str, max_posts: int = 5) -> str:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        markdown = f"""## 📝 Latest Blog Posts / 最新博客文章

*Last Updated: {current_time}*

"""
        
        for i, article in enumerate(articles[:max_posts], 1):
            markdown += f"**{i}.** [{article['title']}]({article['link']}) - *{article['date']}*\n\n"
        
        return markdown
    
    def update_readme(self, readme_path: str = "README.md") -> Tuple[bool, List[CheckResult]]:
        if not os.path.exists(readme_path):
            self.logger.error(f"README file not found: {readme_path}")
            return False, []
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        updated_content = original_content
        check_results = []
        has_new_content = False
        
        for feed in self.rss_feeds:
            if not feed.get("enabled", True):
                self.logger.info(f"Skipping disabled feed: {feed['name']}")
                continue
            
            articles = self.fetch_rss_feed(feed["url"])
            
            if not articles:
                result = CheckResult(
                    status=UpdateStatus.ERROR,
                    timestamp=datetime.now().isoformat(),
                    feed_name=feed["name"],
                    articles_count=0,
                    new_articles=[],
                    error_message="Failed to fetch RSS feed"
                )
                check_results.append(result)
                self.history_manager.add_check_result(result)
                continue
            
            has_changes, new_articles, content_hash = self.change_detector.detect_changes(
                feed["name"], articles
            )
            
            if has_changes and new_articles:
                has_new_content = True
                self.notification_manager.notify_new_content(feed["name"], new_articles)
            
            result = CheckResult(
                status=UpdateStatus.NEW_CONTENT if has_new_content else UpdateStatus.NO_CHANGE,
                timestamp=datetime.now().isoformat(),
                feed_name=feed["name"],
                articles_count=len(articles),
                new_articles=new_articles,
                content_hash=content_hash
            )
            check_results.append(result)
            self.history_manager.add_check_result(result)
            
            new_section = self.generate_markdown_section(
                articles, feed["name"], feed.get("max_posts", 5)
            )
            
            start_marker = f"<!-- {feed['section_marker']} -->"
            end_marker = f"<!-- {feed['section_marker'].replace('START', 'END')} -->"
            
            pattern = re.compile(
                re.escape(start_marker) + r'[\s\S]*?' + re.escape(end_marker),
                re.DOTALL
            )
            
            replacement = f"{start_marker}\n{new_section}\n{end_marker}"
            
            if pattern.search(updated_content):
                updated_content = pattern.sub(replacement, updated_content)
                self.logger.info(f"Updated section for {feed['name']}")
            else:
                self.logger.warning(f"Markers not found for {feed['name']}, appending to end")
                updated_content += f"\n\n{replacement}"
        
        if original_content != updated_content:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            self.logger.info("README.md updated successfully")
            return True, check_results
        
        self.logger.info("No changes to README.md")
        return False, check_results
    
    def run(self) -> int:
        self.logger.info("=" * 50)
        self.logger.info("Starting RSS update check")
        self.logger.info(f"Check mode: {self.check_mode}")
        self.logger.info(f"Feeds configured: {len(self.rss_feeds)}")
        
        for feed in self.rss_feeds:
            status = "enabled" if feed.get("enabled", True) else "disabled"
            self.logger.info(f"  - {feed['name']}: {feed['url']} ({status})")
        
        success, results = self.update_readme()
        
        has_new_content = any(
            r.status == UpdateStatus.NEW_CONTENT for r in results
        )
        
        if has_new_content:
            print("NEW_CONTENT_DETECTED=true")
        
        if success:
            print("CONTENT_UPDATED=true")
            self.logger.info("Update completed with changes")
            return 0
        else:
            self.logger.info("Update completed, no changes needed")
            return 0 if not any(r.status == UpdateStatus.ERROR for r in results) else 1


def main():
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    parser = argparse.ArgumentParser(description='RSS Feed Updater with Change Detection')
    parser.add_argument('--config', '-c', default='rss_config.json', help='Configuration file path')
    parser.add_argument('--check-mode', action='store_true', help='Run in check mode (detect changes only)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--force', '-f', action='store_true', help='Force update regardless of changes')
    
    args = parser.parse_args()
    
    updater = RSSUpdater(config_file=args.config, check_mode=args.check_mode)
    
    if args.verbose:
        updater.logger.logger.setLevel(logging.DEBUG)
    
    exit_code = updater.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
