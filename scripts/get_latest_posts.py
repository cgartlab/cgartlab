#!/usr/bin/env python3
"""
简化版：获取最新博客文章列表（改进版）
参考 tw93/tw93 的实现方式，支持多个RSS源
- 使用正则块替换而非简单的标记替换
- 支持多个RSS源聚合
- 完善的错误处理和日志
- 遇到错误时返回非0退出码
"""

import requests
import feedparser
import re
import sys
import pathlib
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

root = pathlib.Path(__file__).parent.parent.resolve()


def replace_chunk(content, marker, chunk, inline=False):
    """使用正则表达式替换README中的内容块"""
    # 支持多种标记格式
    patterns_and_replacements = [
        # 格式1: <!-- BLOG_POSTS_START -->...<!-- BLOG_POSTS_END -->
        (r"<!-- {}_START -->.*?<!-- {}_END -->".format(marker.upper(), marker.upper()),
         "<!-- {}_START -->\n{}<!-- {}_END -->".format(marker.upper(), chunk, marker.upper())),
        # 格式2: <!-- blog starts -->...<!-- blog ends -->
        (r"<!-- {} starts -->.*?<!-- {} ends -->".format(marker, marker),
         "<!-- {} starts -->{}<!-- {} ends -->".format(marker, chunk, marker)),
    ]
    
    result = content
    found = False
    for pattern, replacement in patterns_and_replacements:
        new_result = re.sub(pattern, replacement, result, flags=re.DOTALL)
        if new_result != result:
            result = new_result
            found = True
            break
    
    if not found:
        print(f"[warning] 未找到标记 {marker}，内容可能未被替换")
    return result


def fetch_posts_from_feed(feed_url: str, max_posts: int = 5) -> list:
    """从单个RSS源获取文章列表"""
    try:
        logger.info(f"正在获取RSS源: {feed_url}")
        headers = {"User-Agent": "Mozilla/5.0 (compatible; cgartlab/1.0)"}
        
        # 增加超时设置
        resp = requests.get(feed_url, headers=headers, timeout=(10, 30))
        resp.raise_for_status()
        
        feed = feedparser.parse(resp.content)
        entries = feed.get("entries", [])
        
        if not entries:
            logger.warning(f"RSS源 {feed_url} 未找到文章条目")
            return []
        
        posts = []
        for entry in entries[:max_posts]:
            title = entry.get("title", "无标题").strip()
            link = entry.get("link", "#")
            
            # 优先使用 published_parsed，其次 updated_parsed
            pub_time = entry.get("published_parsed") or entry.get("updated_parsed")
            if pub_time:
                pub_str = datetime(*pub_time[:6]).strftime("%Y-%m-%d")
            else:
                pub_str = "未知时间"
            
            posts.append({
                "title": title,
                "url": link,
                "published": pub_str
            })
        
        logger.info(f"成功从 {feed_url} 获取了 {len(posts)} 篇文章")
        return posts
        
    except requests.Timeout:
        logger.error(f"获取 {feed_url} 超时（>30秒），可能是网络问题")
        return []
    except requests.RequestException as e:
        logger.error(f"网络请求失败 {feed_url}: {e}")
        return []
    except Exception as e:
        logger.error(f"处理RSS源 {feed_url} 时发生未知错误: {e}")
        return []


def build_blog_content(feeds: dict, max_posts_per_feed: int = 5) -> str:
    """从多个RSS源构建博客内容"""
    all_posts = []
    
    logger.info(f"开始从 {len(feeds)} 个RSS源获取文章")
    
    for feed_name, feed_url in feeds.items():
        posts = fetch_posts_from_feed(feed_url, max_posts_per_feed)
        all_posts.extend(posts)
    
    if not all_posts:
        logger.error("未获取到任何文章，所有RSS源可能都失败了")
        return ""
    
    # 按日期排序（最新优先）
    all_posts.sort(key=lambda x: x["published"], reverse=True)
    
    logger.info(f"成功获取了 {len(all_posts)} 篇文章，正在构建Markdown内容")
    
    # 构建Markdown
    lines = ["## 📝 Latest Blog Posts / 最新博客文章", ""]
    lines.append(f"*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")
    
    for i, post in enumerate(all_posts[:10], 1):  # 显示最多10篇
        lines.append(f"**{i}.** [{post['title']}]({post['url']}) - *{post['published']}*")
        lines.append("")
    
    return "\n".join(lines)


def update_readme(feeds: dict = None) -> int:
    """更新README.md中的博客列表，返回退出码"""
    if feeds is None:
        feeds = {
            "cgartlab": "https://cgartlab.com/rss.xml"
        }
    
    logger.info("开始更新README.md中的博客列表")
    
    # 构建博客内容
    blog_content = build_blog_content(feeds)
    if not blog_content:
        logger.error("博客内容为空，跳过更新")
        return 1
    
    # 读取README
    readme_path = root / "README.md"
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()
        logger.info("成功读取README.md文件")
    except FileNotFoundError:
        logger.error(f"README.md文件不存在: {readme_path}")
        return 1
    except Exception as e:
        logger.error(f"无法读取README.md: {e}")
        return 1
    
    # 替换内容块
    updated_content = replace_chunk(readme_content, "BLOG_POSTS", blog_content)
    
    # 检查是否有实际变更
    if updated_content == readme_content:
        logger.info("README.md 已是最新，无需更新")
        return 0
    
    # 写入更新
    try:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        logger.info("README.md 已成功更新")
        return 2
    except Exception as e:
        logger.error(f"写入README.md失败: {e}")
        return 1


if __name__ == "__main__":
    exit_code = update_readme()
    
    # 返回退出码：0=成功/无变更, 1=失败, 2=已更新
    if exit_code == 0 or exit_code == 2:
        sys.exit(0)
    else:
        sys.exit(1)