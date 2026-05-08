# CGArtLab Code Wiki

> 本文档为 CGArtLab 个人博客站点的结构化代码百科，涵盖项目架构、模块职责、关键类与函数、依赖关系及运行方式。

---

## 目录

1. [项目概述](#1-项目概述)
2. [项目结构](#2-项目结构)
3. [整体架构](#3-整体架构)
4. [模块职责详解](#4-模块职责详解)
   - 4.1 [核心更新引擎 (rss_updater.py)](#41-核心更新引擎-rss_updaterpy)
   - 4.2 [配置文件 (rss_config.json)](#42-配置文件-rss_configjson)
   - 4.3 [GitHub Actions 工作流](#43-github-actions-工作流)
5. [关键类与函数](#5-关键类与函数)
   - 5.1 [数据模型](#51-数据模型)
   - 5.2 [日志系统](#52-日志系统)
   - 5.3 [历史管理](#53-历史管理)
   - 5.4 [变更检测](#54-变更检测)
   - 5.5 [通知系统](#55-通知系统)
   - 5.6 [RSS 更新器主类](#56-rss-更新器主类)
6. [依赖关系](#6-依赖关系)
7. [运行方式](#7-运行方式)
   - 7.1 [本地运行](#71-本地运行)
   - 7.2 [GitHub Actions 自动运行](#72-github-actions-自动运行)
8. [数据流与执行流程](#8-数据流与执行流程)
9. [扩展与定制](#9-扩展与定制)

---

## 1. 项目概述

CGArtLab 是一个个人博客站点仓库，核心功能是通过 **RSS 订阅更新器** 自动获取博客最新文章，并动态更新 `README.md` 文件中的文章列表。项目采用 Python 3.11 开发，结合 GitHub Actions 实现全自动化的内容同步。

### 核心特性

- **自动 RSS 获取**：支持多源 RSS 订阅，自动获取最新文章
- **智能变更检测**：基于内容哈希比对，仅在有新内容时更新
- **多级容错策略**：直连 → Jina AI 代理 → feedparser 直连的三层降级策略
- **历史记录管理**：30 天检查历史缓存，支持增量检测
- **通知机制**：支持 Webhook 和 Telegram 通知（可选）
- **GitHub Actions 集成**：每 4 小时自动检查，支持手动触发

---

## 2. 项目结构

```
cgartlab/
├── .github/
│   └── workflows/
│       └── update-blog-posts.yml    # GitHub Actions 工作流配置
├── .gitignore                        # Git 忽略规则
├── AGENTS.md                         # 开发代理说明文档
├── CODE_WIKI.md                      # 本代码百科文档
├── README.md                         # 项目主页（自动更新博客列表）
├── requirements.txt                  # Python 依赖
├── rss_config.json                   # RSS 源配置文件
├── rss_updater.py                    # 核心更新脚本
├── telegram-qr-code.png              # Telegram 二维码
└── wachat-qr-code.png                # 微信二维码
```

### 运行时生成目录

```
.rss_history/                         # RSS 历史记录目录
├── check_history.json                # 检查历史记录
├── rss_updater.log                   # 运行日志
└── *.lock                            # 文件锁（并发控制）
```

---

## 3. 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        触发层 (Trigger)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   定时触发    │  │   推送触发    │  │   手动触发        │  │
│  │ (每4小时)    │  │ (文件变更)   │  │ (workflow_dispatch)│  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    核心引擎层 (Core Engine)                   │
│                    ┌─────────────────┐                       │
│                    │   RSSUpdater    │                       │
│                    │   (主控制器)     │                       │
│                    └────────┬────────┘                       │
│                             │                                │
│         ┌───────────────────┼───────────────────┐            │
│         ▼                   ▼                   ▼            │
│  ┌─────────────┐   ┌───────────────┐   ┌──────────────┐    │
│  │ RSSLogger   │   │HistoryManager │   │ContentChange │    │
│  │  (日志系统)  │   │  (历史管理)   │   │  Detector    │    │
│  └─────────────┘   └───────────────┘   │ (变更检测)   │    │
│                                        └──────────────┘    │
│                                                             │
│  ┌─────────────┐   ┌───────────────┐   ┌──────────────┐    │
│  │  Feed Fetch │   │  Markdown Gen │   │ Notification │    │
│  │  (RSS获取)  │   │  (文档生成)   │   │  Manager     │    │
│  │             │   │               │   │  (通知管理)  │    │
│  │ • 直连      │   │               │   │              │    │
│  │ • 代理      │   │               │   │ • Webhook   │    │
│  │ • feedparser│   │               │   │ • Telegram  │    │
│  └─────────────┘   └───────────────┘   └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      数据层 (Data Layer)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ README.md    │  │rss_config.json│  │ .rss_history/   │  │
│  │ (展示层)     │  │ (配置层)     │  │ (历史缓存)       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 架构模式

项目采用 **分层架构 + 管道模式**：

1. **触发层**：通过 GitHub Actions 或本地命令触发执行
2. **核心引擎层**：`RSSUpdater` 作为主控制器，协调各子系统完成 RSS 获取、变更检测、内容生成
3. **数据层**：README.md 作为展示载体，`.rss_history/` 作为状态缓存

---

## 4. 模块职责详解

### 4.1 核心更新引擎 (rss_updater.py)

项目唯一的核心代码文件，包含全部业务逻辑。按职责可划分为以下子模块：

| 子模块 | 类/函数 | 职责 |
|--------|---------|------|
| 数据模型 | `Article`, `CheckResult` | 定义 RSS 文章和检查结果的数据结构 |
| 枚举定义 | `UpdateStatus` | 定义更新状态枚举 |
| 日志系统 | `RSSLogger` | 统一日志记录，支持控制台和文件双输出 |
| 历史管理 | `HistoryManager` | 检查历史的持久化、读取、清理，含并发锁控制 |
| 变更检测 | `ContentChangeDetector` | 基于 SHA-256 哈希的内容比对，识别新增文章 |
| 通知系统 | `NotificationManager` | 支持 Webhook 和 Telegram 通知发送 |
| 主控制器 | `RSSUpdater` | 配置加载、RSS 获取、内容更新、文件写入的编排 |
| 命令入口 | `main()` | CLI 参数解析和程序入口 |

### 4.2 配置文件 (rss_config.json)

JSON 格式配置文件，定义 RSS 源和系统设置：

```json
{
  "feeds": [...],        // RSS 源列表
  "settings": {...},     // 系统设置
  "notifications": {...} // 通知配置（可选）
}
```

### 4.3 GitHub Actions 工作流

`.github/workflows/update-blog-posts.yml` 定义自动化流水线：

- **触发条件**：定时（每4小时）、推送（特定文件变更）、手动触发
- **执行步骤**：检出代码 → 安装依赖 → 运行检查 → 提交变更 → 生成报告
- **并发控制**：同一工作流新运行会取消进行中的运行

---

## 5. 关键类与函数

### 5.1 数据模型

#### `UpdateStatus` (Enum)

更新状态枚举，标识单次检查的结果状态。

| 成员 | 值 | 说明 |
|------|-----|------|
| `NEW_CONTENT` | `"new_content"` | 检测到全新文章 |
| `UPDATED` | `"updated"` | 内容有更新（非全新文章） |
| `NO_CHANGE` | `"no_change"` | 无变化 |
| `ERROR` | `"error"` | 执行出错 |

#### `Article` (dataclass)

RSS 文章数据类，封装单篇文章的元数据。

**字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | `str` | 文章标题 |
| `link` | `str` | 文章链接 |
| `date` | `str` | 发布日期（YYYY-MM-DD 格式） |
| `description` | `str` | 文章摘要 |
| `author` | `str` | 作者 |
| `guid` | `str` | 全局唯一标识 |

**方法：**

- `from_dict(data: Dict) -> Article`: 从字典反序列化
- `to_dict() -> Dict`: 序列化为字典

#### `CheckResult` (dataclass)

单次 RSS 源检查的结果封装。

**字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | `UpdateStatus` | 检查状态 |
| `timestamp` | `str` | 检查时间戳（ISO 格式） |
| `feed_name` | `str` | RSS 源名称 |
| `articles_count` | `int` | 获取到的文章总数 |
| `new_articles` | `List[Article]` | 新增文章列表 |
| `error_message` | `Optional[str]` | 错误信息（如有） |
| `content_hash` | `Optional[str]` | 内容哈希值 |

---

### 5.2 日志系统

#### `RSSLogger`

统一日志管理器，支持控制台和文件双通道输出。

**初始化参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `log_dir` | `str` | `".rss_history"` | 日志文件目录 |
| `log_level` | `str` | `"INFO"` | 日志级别 |

**方法：**

| 方法 | 说明 |
|------|------|
| `info(msg)` | 记录 INFO 级别日志 |
| `error(msg)` | 记录 ERROR 级别日志 |
| `warning(msg)` | 记录 WARNING 级别日志 |
| `debug(msg)` | 记录 DEBUG 级别日志 |

**日志文件位置：** `.rss_history/rss_updater.log`

---

### 5.3 历史管理

#### `HistoryManager`

检查历史的持久化管理，支持文件锁防止并发冲突。

**初始化参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `history_dir` | `str` | `".rss_history"` | 历史文件目录 |
| `logger` | `Optional[RSSLogger]` | `None` | 日志器实例 |

**核心方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `load_history` | `() -> Dict` | 加载历史记录，带文件锁 |
| `save_history` | `(history: Dict) -> None` | 保存历史记录，自动清理30天前数据 |
| `get_last_content_hash` | `(feed_name: str) -> Optional[str]` | 获取指定源的上次内容哈希 |
| `set_last_content_hash` | `(feed_name: str, content_hash: str) -> None` | 设置内容哈希 |
| `add_check_result` | `(result: CheckResult) -> None` | 添加检查结果到历史 |
| `get_recent_checks` | `(feed_name: str, limit: int = 10) -> List[Dict]` | 获取最近的检查记录 |

**并发控制：**

- **Unix/Linux/macOS**：使用 `fcntl.flock` 文件锁
- **Windows**：使用文件存在检查（简化实现）

---

### 5.4 变更检测

#### `ContentChangeDetector`

基于哈希算法的内容变更检测器。

**初始化参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `history_manager` | `HistoryManager` | 必填 | 历史管理器实例 |
| `logger` | `Optional[RSSLogger]` | `None` | 日志器实例 |

**核心方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `compute_content_hash` | `(articles: List[Article]) -> str` | 计算文章列表的 SHA-256 哈希 |
| `detect_changes` | `(feed_name: str, current_articles: List[Article]) -> Tuple[bool, List[Article], str]` | 检测内容变更，返回 `(是否有变化, 新增文章, 当前哈希)` |
| `_identify_new_articles` | `(feed_name: str, current_articles: List[Article]) -> List[Article]` | 从历史记录中识别真正的新文章 |

**变更检测逻辑：**

1. 计算当前文章列表的 SHA-256 哈希
2. 与历史哈希比对：
   - 无历史记录 → 视为首次，存储哈希
   - 哈希一致 → 无变化
   - 哈希不一致 → 从历史中识别新增文章，更新哈希

---

### 5.5 通知系统

#### `NotificationManager`

新内容通知管理器，支持 Webhook 和 Telegram 两种渠道。

**初始化参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `config` | `Dict` | 必填 | 配置字典（含 notifications 节点） |
| `logger` | `Optional[RSSLogger]` | `None` | 日志器实例 |

**核心方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `notify_new_content` | `(feed_name: str, new_articles: List[Article]) -> None` | 发送新内容通知 |
| `_send_webhook_notification` | `(webhook_url: str, feed_name: str, new_articles: List[Article]) -> None` | 发送 Webhook POST 请求 |
| `_send_telegram_notification` | `(token: str, chat_id: str, feed_name: str, new_articles: List[Article]) -> None` | 发送 Telegram 消息 |

**Webhook Payload 格式：**

```json
{
  "feed_name": "CGArtLab Blog",
  "new_articles_count": 3,
  "articles": [...],
  "timestamp": "2026-05-08T10:00:00"
}
```

---

### 5.6 RSS 更新器主类

#### `RSSUpdater`

系统主控制器，负责配置加载、RSS 获取、内容更新和文件写入的全流程编排。

**初始化参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `config_file` | `str` | `"rss_config.json"` | 配置文件路径 |
| `check_mode` | `bool` | `False` | 检查模式（只检测不写入） |
| `force` | `bool` | `False` | 强制更新模式 |

**核心方法：**

| 方法 | 签名 | 说明 |
|------|------|------|
| `_load_config` | `() -> Dict` | 加载并验证配置文件，失败时返回默认配置 |
| `_validate_config` | `(config: Dict) -> bool` | 验证配置结构合法性 |
| `_create_session_with_retry` | `() -> requests.Session` | 创建带重试策略的 HTTP Session |
| `_build_request_headers` | `(feed_url: str) -> Dict` | 构建 RSS 请求头（含 User-Agent、Referer） |
| `fetch_rss_feed` | `(feed_url: str) -> Optional[List[Article]]` | 获取 RSS 源（三级降级策略） |
| `_fetch_with_direct_connection` | `(session, feed_url, headers, timeout) -> Optional[List[Article]]` | 直接连接获取 |
| `_fetch_with_proxy` | `(session, feed_url, headers, timeout) -> Optional[List[Article]]` | 通过 Jina AI 代理获取 |
| `_fetch_with_feedparser_direct` | `(feed_url: str) -> Optional[List[Article]]` | feedparser 直连解析 |
| `_parse_feed_entries` | `(feed) -> List[Article]` | 解析 feedparser 条目为 Article 列表 |
| `generate_markdown_section` | `(articles, feed_name, max_posts) -> str` | 生成 Markdown 格式的文章列表 |
| `_update_content_section` | `(content, new_section, section_marker, feed_name) -> str` | 替换 README 中标记区域的内容 |
| `_write_readme_file` | `(readme_path, content) -> bool` | 原子写入 README 文件 |
| `update_readme` | `(readme_path="README.md") -> Tuple[bool, List[CheckResult]]` | 更新 README 的主逻辑 |
| `_process_single_feed` | `(feed, updated_content) -> Tuple[str, Optional[CheckResult]]` | 处理单个 RSS 源 |
| `run` | `() -> int` | 程序主入口，返回退出码 |

**RSS 获取三级降级策略：**

```
1. 直接连接 (requests + feedparser)
   ↓ 失败
2. Jina AI 代理 (https://r.jina.ai/{url})
   ↓ 失败
3. feedparser 直接解析
   ↓ 失败
   返回 None
```

**退出码定义：**

| 退出码 | 含义 |
|--------|------|
| `0` | 成功（含无变化情况） |
| `1` | 执行过程中出现错误 |

---

## 6. 依赖关系

### Python 依赖

| 包名 | 版本 | 用途 |
|------|------|------|
| `feedparser` | `6.0.11` | RSS/Atom  feed 解析 |
| `requests` | `2.32.3` | HTTP 请求（RSS 获取、Webhook 通知） |
| `urllib3` | `>=2.6.0,<3.0.0` | HTTP 客户端底层依赖 |

### 标准库依赖

| 模块 | 用途 |
|------|------|
| `argparse` | 命令行参数解析 |
| `datetime` | 日期时间处理 |
| `hashlib` | SHA-256 哈希计算 |
| `json` | JSON 配置读写 |
| `logging` | 日志系统底层 |
| `re` | 正则表达式（标记区域匹配） |
| `sys`, `os`, `io` | 系统交互、文件操作 |
| `pathlib` | 跨平台路径处理 |
| `typing` | 类型注解 |
| `dataclasses` | 数据类定义 |
| `enum` | 枚举定义 |
| `urllib.parse` | URL 解析 |

### 可选依赖

| 模块 | 平台 | 用途 |
|------|------|------|
| `fcntl` | Unix/Linux/macOS | 文件锁（并发控制） |

---

## 7. 运行方式

### 7.1 本地运行

**安装依赖：**

```bash
pip install -r requirements.txt
```

**基本用法：**

```bash
# 标准模式：检测变化并更新 README.md
python rss_updater.py

# 检查模式：只检测变化，不更新文件
python rss_updater.py --check-mode

# 强制更新：无论是否有变化都更新
python rss_updater.py --force

# 详细输出
python rss_updater.py --verbose

# 指定配置文件
python rss_updater.py --config custom_config.json
```

**命令行参数：**

| 参数 | 简写 | 说明 |
|------|------|------|
| `--config` | `-c` | 指定配置文件路径 |
| `--check-mode` | - | 检查模式（只检测不写入） |
| `--verbose` | `-v` | 启用 DEBUG 级别日志 |
| `--force` | `-f` | 强制更新 |

### 7.2 GitHub Actions 自动运行

**触发条件：**

| 触发方式 | 配置 |
|----------|------|
| 定时触发 | 每 4 小时 (`0 */4 * * *`) |
| 推送触发 | 推送至 main 分支，且变更 `rss_config.json`、工作流文件或 `rss_updater.py` |
| 手动触发 | `workflow_dispatch`，可选 `force_update` 参数 |

**工作流步骤：**

1. **检出代码**：`actions/checkout@v4`（fetch-depth: 2）
2. **设置 Python**：`actions/setup-python@v5`（Python 3.11）
3. **安装依赖**：`pip install -r requirements.txt`
4. **缓存历史**：`actions/cache@v4`（缓存 `.rss_history` 目录）
5. **运行检查**：`python rss_updater.py --check-mode`
6. **检查变更**：`git diff --exit-code README.md`
7. **提交推送**：自动提交并推送 README.md 变更
8. **生成报告**：输出工作流摘要

---

## 8. 数据流与执行流程

### 单次检查完整流程

```
开始
  │
  ▼
加载配置 (rss_config.json)
  │
  ▼
遍历配置的 RSS 源
  │
  ├──► 检查源是否启用
  │      │
  │      ▼
  │    获取 RSS (三级降级策略)
  │      │
  │      ├──► 直接连接
  │      ├──► Jina AI 代理
  │      └──► feedparser 直连
  │      │
  │      ▼
  │    解析文章列表
  │      │
  │      ▼
  │    变更检测 (SHA-256 哈希比对)
  │      │
  │      ├──► 首次检查 → 存储哈希
  │      ├──► 无变化 → 跳过
  │      └──► 有变化 → 识别新文章
  │            │
  │            ▼
  │          发送通知 (如启用)
  │            │
  │            ▼
  │          生成 Markdown 区块
  │            │
  │            ▼
  │          替换 README 标记区域
  │
  ▼
所有源处理完毕
  │
  ├──► 检查模式 → 输出检测结果，结束
  │
  └──► 正常模式
         │
         ├──► 有变更 → 原子写入 README.md
         │
         └──► 无变更 → 结束
```

### README.md 标记替换机制

README.md 中使用 HTML 注释作为标记：

```markdown
<!-- BLOG_POSTS_START -->
## 📝 Latest Blog Posts / 最新博客文章

*Last Updated: 2026-05-02 20:30:10*

**1.** [文章标题](链接) - *日期*
...
<!-- BLOG_POSTS_END -->
```

替换逻辑：正则匹配 `<!-- {MARKER} -->` 和 `<!-- {MARKER.replace('START', 'END')} -->` 之间的内容，替换为新生成的 Markdown。

---

## 9. 扩展与定制

### 添加新的 RSS 源

编辑 `rss_config.json`，在 `feeds` 数组中添加：

```json
{
  "name": "My New Feed",
  "url": "https://example.com/rss.xml",
  "section_marker": "NEW_POSTS_START",
  "max_posts": 5,
  "enabled": true
}
```

并在 `README.md` 中添加对应标记：

```markdown
<!-- NEW_POSTS_START -->
<!-- NEW_POSTS_END -->
```

### 启用通知

编辑 `rss_config.json` 的 `notifications` 节点：

```json
{
  "notifications": {
    "enabled": true,
    "webhook_url": "https://hooks.example.com/webhook",
    "telegram_token": "YOUR_BOT_TOKEN",
    "telegram_chat_id": "YOUR_CHAT_ID"
  }
}
```

### 调整检查频率

修改 GitHub Actions 工作流中的 cron 表达式：

```yaml
on:
  schedule:
    - cron: '0 */2 * * *'  # 每 2 小时
```

---

*本文档基于代码分析自动生成，最后更新：2026-05-08*
