# CGArtLab Code Wiki

> CGArtLab 博客 RSS 自动化工具的结构化代码百科 — 10 模块架构，Pydantic v2 数据层，filelock 并发安全。

---

## 目录

1. [项目概述](#1-项目概述)
2. [项目结构](#2-项目结构)
3. [模块职责详解](#3-模块职责详解)
    - 3.1 [models.py — 数据模型与配置加载](#31-modelspy--数据模型与配置加载)
    - 3.2 [cli.py — 命令行接口](#32-clipy--命令行接口)
    - 3.3 [fetcher.py — RSS 订阅获取](#33-fetcherpy--rss-订阅获取)
    - 3.4 [detector.py — 变更检测](#34-detectorpy--变更检测)
    - 3.5 [history.py — 历史管理](#35-historypy--历史管理)
    - 3.6 [renderer.py — Markdown 渲染](#36-rendererpy--markdown-渲染)
    - 3.7 [updater.py — 主协调器](#37-updaterpy--主协调器)
    - 3.8 [notifier.py — 通知系统](#38-notifierpy--通知系统)
    - 3.9 [logger.py — 日志配置](#39-loggerpy--日志配置)
    - 3.10 [rss_updater.py — 根入口](#310-rss_updaterpy--根入口)
4. [数据流与执行流程](#4-数据流与执行流程)
5. [配置说明](#5-配置说明)
6. [CLI 接口](#6-cli-接口)
7. [CI/CD 工作流](#7-cicd-工作流)
8. [测试体系](#8-测试体系)
9. [依赖关系](#9-依赖关系)

---

## 1. 项目概述

CGArtLab RSS 自动化工具从 RSS 订阅源抓取博客文章，自动更新 `README.md`。已从单文件重构为 10 模块 Python 包（~930 行）。

### 核心特性

- **三级获取策略**：直连 → Jina AI 代理 → feedparser 直连
- **智能变更检测**：SHA-256 哈希 + GUID 双重校验
- **并发安全**：`filelock` 跨平台文件锁 + `tempfile` + `os.replace` 原子写入
- **历史管理**：30 天滚动检查记录，GUID 增量追踪
- **通知系统**：Webhook / Telegram / Bark，异步并发分发
- **CI 集成**：每 8 小时自动检查，lint → typecheck → test → coverage 全流程

---

## 2. 项目结构

```
cgartlab/
├── .github/workflows/
│   ├── update-blog-posts.yml    # 博客更新（定时/手动/推送触发）
│   ├── lint-and-test.yml        # CI 流水线（lint + typecheck + test）
│   └── argus-review.yml         # PR 自动审查
│
├── rss_updater/                 # 核心包（10 模块）
│   ├── __init__.py              # 空包标记（无 re-export）
│   ├── cli.py                   # CLI 参数解析 + 入口
│   ├── models.py                # Pydantic v2 数据模型
│   ├── fetcher.py               # RSS 三层获取
│   ├── detector.py              # 哈希 + GUID 变更检测
│   ├── history.py               # JSON 历史持久化 + filelock
│   ├── renderer.py              # Markdown 区域替换
│   ├── updater.py               # 主协调器
│   ├── notifier.py              # 通知分发（ABC + Registry）
│   └── logger.py                # 日志配置
│
├── tests/                       # 9 个测试模块，109 个测试
│   ├── conftest.py              # （待补充共享 fixtures）
│   ├── test_cli.py
│   ├── test_models.py
│   ├── test_fetcher.py
│   ├── test_detector.py
│   ├── test_history.py
│   ├── test_renderer.py
│   ├── test_logger.py
│   ├── test_notifier.py
│   └── test_updater.py
│
├── rss_updater.py               # 6 行薄封装，委托给 cli.main()
├── rss_config.json              # RSS 源配置
├── pyproject.toml               # 项目元数据 + 工具配置
├── requirements.txt             # pip 依赖锁定
├── assets/                      # 静态资源
│   ├── divider.svg              # 分隔线
│   ├── wechat-qr-code.png
│   └── telegram-qr-code.png
├── AGENTS.md                    # 开发代理指南
├── CODE_WIKI.md                 # 本文件
└── README.md                    # 项目主页（自动更新博客列表）
```

### 运行时生成

```
.rss_history/
├── history.json                 # 检查历史 + 已知 GUID + 内容哈希
├── rss_updater.log              # 运行日志
└── history.lock                 # filelock 并发锁
```

---

## 3. 模块职责详解

### 3.1 `models.py` — 数据模型与配置加载

**行数**: 84 | **公共类**: 6 | **函数**: 1

Pydantic v2 模型层，负责所有数据结构定义和 JSON 配置反序列化。

| 类 | 关键字段 | 说明 |
|---|---|---|
| `Article` | `title`, `link`, `date`, `description`, `author`, `guid` | 文章数据 |
| `FeedConfig` | `name`, `url`, `section_marker`, `max_posts`, `enabled` | 订阅源配置 |
| `CheckResult` | `status` (validated: success/error/no_change/partial), `timestamp`, `feed_name`, `new_articles`, `content_hash` | 检查结果 |
| `Settings` | `check_interval_minutes`, `max_retries`, `timeout_seconds`, `history_dir`, `log_level` | 全局设置 |
| `NotificationChannel` | `type`, `enabled` (+ ConfigDict `extra="allow"`) | 通知渠道 |
| `AppConfig` | `feeds`, `settings`, `notifications` | 聚合配置 |

```python
# 函数签名
def load_config(path: str) -> AppConfig
```

**向后兼容**：`load_config()` 兼容新旧两种 notifications 格式：
- 旧格式：`{"webhook": {"url": "..."}, "telegram": {"token": "..."}}`
- 新格式：`{"channels": [{"type": "webhook", ...}]}`

---

### 3.2 `cli.py` — 命令行接口

**行数**: 141 | **函数**: 5

参数解析、健康检查、程序入口。

```python
def main(argv: list[str] | None = None) -> int
```

| 标志 | 简写 | 默认 | 说明 |
|------|------|------|------|
| `--config` | `-c` | `rss_config.json` | 配置文件路径 |
| `--check-mode` | — | `False` | 仅检测，不写入 |
| `--force` | `-f` | `False` | 跳过检测，强制更新 |
| `--verbose` | `-v` | `False` | DEBUG 日志 |
| `--health-check` | — | `False` | 测试所有源，打印状态表 |

**`health_check()`** 遍历每个启用的订阅源，调用 `FeedFetcher.fetch()`，输出格式化表格（Feed Name / Status / Response Time / Articles / Error）。

**主流程**: `_setup_stdout_utf8()` → `_build_parser()` → `load_config()` → `RSSUpdater.run()`。

---

### 3.3 `fetcher.py` — RSS 订阅获取

**行数**: 140 | **类**: `FeedFetcher`

三层降级获取策略，`requests.Session` 带重试。

```python
class FeedFetcher:
    def __init__(self, session: requests.Session | None = None)

    def fetch(self, feed_url: str, timeout: float = 15.0) -> list[Article] | None
```

**获取策略**:
```
1. _fetch_direct():        session.get(url) + feedparser.parse()
       ↓ 失败
2. _fetch_via_proxy():     session.get(r.jina.ai/{url}) + feedparser.parse()
       ↓ 失败
3. _fetch_feedparser_direct():  feedparser.parse(url, no requests)
       ↓ 失败
   return None
```

**session 属性**: 懒初始化，缓存 `requests.Session` 带 `Retry(3, backoff=1s, status_forcelist=[429,500,502,503,504])`。

**日期解析**: 依次尝试 `published_parsed` → `updated_parsed` → `created_parsed`，全失败返回 `"未知日期"`。

---

### 3.4 `detector.py` — 变更检测

**行数**: 71 | **类**: `ContentChangeDetector`

双层变更检测：粗粒度 SHA-256 哈希 + 细粒度 GUID 追踪。

```python
class ContentChangeDetector:
    @staticmethod
    def compute_hash(articles: list[Article]) -> str

    def detect_changes(
        self, feed_name: str, current_articles: list[Article], history: HistoryManager
    ) -> tuple[bool, list[Article], str]
```

**检测逻辑**:
1. 计算当前文章列表的 SHA-256 哈希（JSON 序列化后取摘要）
2. 与 `history.get_last_content_hash(feed_name)` 比较
3. 哈希一致 → `(False, [], hash)`
4. 哈希不同 → 通过 GUID 集合差异识别新文章 → `(True, new_articles, hash)`

**首次运行**（无已知 GUID）：所有文章标记为新。

---

### 3.5 `history.py` — 历史管理

**行数**: 138 | **类**: `HistoryManager`

JSON 持久化，`filelock` 并发安全，`tempfile.mkstemp` + `os.replace` 原子写入。

```python
class HistoryManager:
    def __init__(self, history_dir: Path)

    def load_history(self) -> dict
    def save_history(self, history: dict) -> None
    def get_last_content_hash(self, feed_name) -> str | None
    def set_last_content_hash(self, feed_name, content_hash) -> None
    def get_known_guids(self, feed_name) -> set[str]
    def add_known_guids(self, feed_name, guids) -> None
    def add_check_result(self, result: CheckResult) -> None
    def get_recent_checks(self, feed_name, limit=10) -> list
```

**JSON 结构**:
```json
{
  "FeedName": {
    "last_content_hash": "sha256hex...",
    "known_guids": ["guid1", "guid2"],
    "checks": [
      {"status": "success", "timestamp": "...", "articles_count": 5}
    ]
  }
}
```

**锁机制**: `FileLock(history.lock, timeout=10)` — 所有读写方法均在锁保护下执行。并发测试使用 20 线程 + `threading.Barrier` 验证。

**清理**: `_cleanup_old_checks()` 在每次 `add_check_result()` 时自动删除超过 30 天的记录。

**原子写入**:
```python
fd, tmp_path = tempfile.mkstemp(dir=str(history_dir), suffix=".tmp")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp_path, target_path)
except Exception:
    with contextlib.suppress(OSError):
        os.unlink(tmp_path)
    raise
```

---

### 3.6 `renderer.py` — Markdown 渲染

**行数**: 60 | **类**: `MarkdownRenderer`

Markdown 文章区域生成与 README 内容替换。

```python
class MarkdownRenderer:
    def _escape_markdown(self, text: str) -> str
    def render_section(
        self, articles: list[Article], feed_name: str = "", max_posts: int = 5
    ) -> str
    def update_content(
        self, content: str, new_section: str, section_marker: str
    ) -> str
```

**区域标记格式**: `<!-- BLOG_POSTS_START --> ... <!-- BLOG_POSTS_END -->`

**替换策略**: 正则 `re.escape(start) + r".*?" + re.escape(end)` + `re.DOTALL`。若标记不存在，则在文件末尾追加。

**Markdown 转义**: `_escape_markdown()` 转义 `[\`*_{}[]()#+\-.!|]` 字符。

---

### 3.7 `updater.py` — 主协调器

**行数**: 163 | **类**: `RSSUpdater`

整个流水线的单点协调器：fetch → detect → render → save → notify。

```python
class RSSUpdater:
    def __init__(self, config: AppConfig, check_mode: bool = False, force: bool = False)

    def _fetch_feed(self, feed: FeedConfig) -> list[Article] | None
    def _process_feed(self, feed: FeedConfig) -> CheckResult
    def update_readme(self, readme_path: str = "README.md") -> tuple[bool, list[CheckResult]]
    def _atomic_write(self, path: str, content: str) -> None
    def run(self) -> int
```

**`update_readme()` 执行流程**:
1. 读取 README.md
2. 遍历每个启用的 FeedConfig:
   - `_process_feed()` → `CheckResult`
   - `history.add_check_result(result)`
   - 若 `status=="success"` 且 `new_articles` 非空:
     - `any_new_content = True`
     - 非 check-mode: `renderer.render_section()` + `renderer.update_content()`
     - `notifier.send_notifications()`
3. 打印 `NEW_CONTENT_DETECTED=true/false`
4. 非 check-mode: 原子写入 README，打印 `CONTENT_UPDATED=true/false`

**`run()` 退出码**: 0（全成功/无变化），1（有错误）

**`_atomic_write()`**: 与 HistoryManager 相同的 `tempfile.mkstemp` + `os.replace` 模式。

---

### 3.8 `notifier.py` — 通知系统

**行数**: 183 | **类**: 5 | **函数**: 1

ABC + Registry 模式，异步并发分发。

```python
class BaseNotifier(ABC):
    @abstractmethod
    async def notify(self, feed_name: str, new_articles: list[Article]) -> None
    @abstractmethod
    def is_configured(self) -> bool

class WebhookNotifier(BaseNotifier)   # POST JSON payload
class TelegramNotifier(BaseNotifier)  # POST sendMessage, Markdown parse_mode
class BarkNotifier(BaseNotifier)      # GET api.day.app/{key}

class NotifierRegistry:
    _registry: dict[str, type[BaseNotifier]]
    @classmethod
    def register(cls, type_name, notifier_cls)
    @classmethod
    def create(cls, channel: NotificationChannel) -> BaseNotifier | None

def send_notifications(
    channels: list[NotificationChannel],
    feed_name: str,
    new_articles: list[Article]
) -> None
```

**内置通知器**:

| 类型 | 配置要求 | 行为 |
|------|---------|------|
| `webhook` | `webhook_url` 非空 | POST JSON `{feed_name, articles, count}` |
| `telegram` | `telegram_token` + `telegram_chat_id` 非空 | 截断至 10 条，Markdown 格式 |
| `bark` | `bark_key` 非空 | 截断至 5 条，GET 请求 |

**分发逻辑**: `asyncio.run(asyncio.gather(*tasks, return_exceptions=True))` — 所有通知器并发执行，单失败不阻断其他通道。未知类型记录警告并跳过。

---

### 3.9 `logger.py` — 日志配置

**行数**: 46 | **类**: `_JsonFormatter` | **函数**: `setup_logging()`

```python
def setup_logging(log_dir: Path, level: str = "INFO", json_format: bool = False) -> None
```

- 创建 `log_dir`
- 配置 `logging.getLogger("rss_updater")`
- 清除已有 handlers
- 添加 StreamHandler（控制台，格式：`time - LEVEL - msg`）
- 添加 FileHandler（文件，支持 JSON 或文本格式）
- 日志文件：`{log_dir}/rss_updater.log`

**命名约定**: 每个模块创建子 logger：`logging.getLogger("rss_updater.fetcher")`，继承自根 `rss_updater`。

---

### 3.10 `rss_updater.py` — 根入口

**行数**: 6 | **函数**: 0

纯委托封装，无业务逻辑：

```python
#!/usr/bin/env python3
from rss_updater.cli import main
import sys
sys.exit(main())
```

---

## 4. 数据流与执行流程

```
rss_updater.py → cli.main()
                     │
                     ├──► load_config() → AppConfig (Pydantic validated)
                     │
                     └──► RSSUpdater(config, check_mode, force)
                              │
                              ├──► 对每个启用的 FeedConfig:
                              │       │
                              │       ├──► FeedFetcher.fetch(url, timeout)
                              │       │       ├── 1. 直连 (requests + feedparser)
                              │       │       ├── 2. 代理 (r.jina.ai + feedparser)
                              │       │       └── 3. feedparser 直连
                              │       │
                              │       ├──► ContentChangeDetector.detect_changes(name, articles, history)
                              │       │       ├── SHA-256 哈希比对
                              │       │       └── GUID 比对 → 新文章列表
                              │       │
                              │       ├──► HistoryManager: 更新 hash + GUIDs + 检查记录
                              │       │
                              │       └──► 若有新内容:
                              │               ├── MarkdownRenderer.render_section()
                              │               ├── MarkdownRenderer.update_content()
                              │               └── notifier.send_notifications()
                              │
                              └──► 非 check-mode 且新内容:
                                      └── _atomic_write(README.md, content)
```

---

## 5. 配置说明

`rss_config.json` 字段表：

| 路径 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `feeds[].url` | string | — | RSS 订阅源 URL |
| `feeds[].section_marker` | string | — | README 注释标记（如 `BLOG_POSTS`） |
| `feeds[].max_posts` | int | 5 | 显示最大文章数（≥1） |
| `feeds[].enabled` | bool | true | 启用/禁用 |
| `settings.check_interval_minutes` | int | 60 | 检查间隔 |
| `settings.max_retries` | int | 3 | 最大重试次数 |
| `settings.timeout_seconds` | float | 15.0 | HTTP 超时 |
| `settings.history_dir` | string | `.rss_history` | 历史目录 |
| `settings.log_level` | string | `INFO` | 日志级别 |
| `notifications[].type` | string | — | `webhook` / `telegram` / `bark` |
| `notifications[].enabled` | bool | true | 启用/禁用通知 |

---

## 6. CLI 接口

```bash
python rss_updater.py                    # 标准运行
python rss_updater.py --check-mode       # 仅检测
python rss_updater.py --force            # 强制更新
python rss_updater.py --health-check     # 健康检查
python rss_updater.py --verbose          # DEBUG 日志
python rss_updater.py -c custom.json     # 自定义配置
```

**退出码**:
- `0`: 全成功（含无变更）
- `1`: 配置加载失败或任意源获取错误

**CI 输出标记**（供 GitHub Actions 解析）:
- `NEW_CONTENT_DETECTED=true/false`
- `CONTENT_UPDATED=true/false`

---

## 7. CI/CD 工作流

### 7.1 更新工作流 (`update-blog-posts.yml`)

| 触发方式 | 配置 |
|---------|------|
| 定时 | `0 0/8 * * *`（每天 00:00 / 08:00 / 16:00 UTC） |
| 推送 | main 分支，变更 `rss_config.json` / `rss_updater/**` / workflow |
| 手动 | `workflow_dispatch`，可选 `force_update` |

**权限**: `contents: write`

**关键步骤**: checkout → Python 3.11 → pip install → 缓存 `.rss_history/` → 运行 updater → 解析输出 → git commit/push（有变更时）

### 7.2 CI 流水线 (`lint-and-test.yml`)

| 触发方式 | 配置 |
|---------|------|
| 推送 | main 分支 |
| PR | main 分支 |
| 手动 | `workflow_dispatch` |

**步骤**: `ruff check` → `ruff format --check` → `mypy` → `pytest --cov` → Codecov

### 7.3 PR 审查 (`argus-review.yml`)

触发 `pull_request` 事件，使用 `cgartlab/argus` action 自动审查。

---

## 8. 测试体系

| 测试模块 | 测试数 | 覆盖内容 |
|---------|--------|---------|
| `test_cli.py` | 18 | 参数解析、main 流程、健康检查 |
| `test_fetcher.py` | 16 | 三层策略、session、日期解析 |
| `test_notifier.py` | 17 | 三种通知器、注册表、异常 |
| `test_updater.py` | 13 | 各模式流程、退出码、原子写入 |
| `test_history.py` | 10 | CRUD、并发（20线程）、清理、边角 |
| `test_renderer.py` | 9 | Markdown 转义、渲染、内容替换 |
| `test_detector.py` | 7 | 哈希、排序敏感、变化检测 |
| `test_logger.py` | 5 | JSON 格式、文件输出 |
| `test_models.py` | 4 | 序列化、校验、配置加载 |
| **合计** | **109** | — |

**并发测试**: `test_history.py` 使用 `threading.Barrier` 同步 20 线程验证 `filelock` 安全性。

**Mock 策略**: `unittest.mock.patch` + `MagicMock`，无外部 HTTP mock 库。

---

## 9. 依赖关系

```
┌──────────┐    ┌────────┐    ┌──────────┐    ┌──────────┐
│ fetcher  │◄───│updater │───►│ renderer │    │ notifier │
│  (session │    │        │    │ (markdown│    │  (async) │
│   + 3级)  │    │        │    │  + regex)│    │          │
└──────────┘    └───┬────┘    └──────────┘    └──────────┘
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
    ┌────────┐ ┌────────┐ ┌────────┐
    │detector│ │history │ │models  │
    │ (hash) │ │(filelock)│ │(Pydantic)│
    └────────┘ └────────┘ └────────┘

rss_updater.py → cli.py → updater.py + models.py
```

**无循环依赖**: `updater.py` 是唯一的汇聚点，导入所有模块但不被其他模块导入（除 `cli.py`）。

### 生产依赖

| 包 | 版本 | 用途 |
|----|------|------|
| `feedparser` | ≥6.0,<7.0 | RSS/Atom 解析 |
| `requests` | ≥2.32,<3.0 | HTTP 客户端 |
| `urllib3` | ≥2.6,<3.0 | 传输层 |
| `pydantic` | ≥2.0,<3.0 | 数据验证 |
| `filelock` | ≥3.0,<4.0 | 文件锁 |

### 开发依赖

| 包 | 版本 | 用途 |
|----|------|------|
| `pytest` | ≥8.0 | 测试框架 |
| `pytest-cov` | ≥5.0 | 覆盖率 |
| `ruff` | ≥0.6 | 检查/格式化 |
| `mypy` | ≥1.10 | 类型检查 |

### 标准库
`argparse`, `datetime`, `hashlib`, `json`, `logging`, `re`, `os`, `sys`, `pathlib`, `typing`, `tempfile`, `contextlib`, `threading`, `asyncio`