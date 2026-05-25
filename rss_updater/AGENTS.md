# rss_updater — Core Package

**分层**: 内容自动化 — RSS 抓取、变更检测、渲染、通知

## OVERVIEW

RSS 自动化核心包，10 个模块 ~830 行。负责从 RSS 源抓取文章、检测内容变更、渲染 Markdown、管理历史记录、分发通知。

## STRUCTURE

```
rss_updater/
├── cli.py        # 参数解析（argparse） + health-check 表格 + main()
├── models.py     # Pydantic v2：Article, CheckResult, FeedConfig, Settings, AppConfig
├── fetcher.py    # FeedFetcher — 3 级 fallback 抓取策略，requests 会话 + 重试
├── detector.py   # ContentChangeDetector — SHA-256 hash 比对
├── updater.py    # RSSUpdater — 编排抓取→检测→渲染→保存→通知
├── renderer.py   # MarkdownRenderer — regex 区间替换
├── history.py    # HistoryManager — JSON 持久化 + FileLock 并发保护
├── notifier.py   # BaseNotifier / WebhookNotifier / TelegramNotifier
└── logger.py     # JSON 或文本格式日志，双路输出（console + file）
```

## CLASS HIERARCHY

| Class | Module | Role |
|-------|--------|------|
| `Article` | models.py | RSS feed article data |
| `CheckResult` | models.py | Per-feed check outcome |
| `FeedConfig` | models.py | Per-feed configuration |
| `AppConfig` | models.py | Full app configuration |
| `FeedFetcher` | fetcher.py | RSS HTTP fetching |
| `ContentChangeDetector` | detector.py | Hash-based change detection |
| `HistoryManager` | history.py | JSON + FileLock persistence |
| `MarkdownRenderer` | renderer.py | Markdown section generation |
| `RSSUpdater` | updater.py | Main orchestration |
| `BaseNotifier` (ABC) | notifier.py | Notification interface |
| `TelegramNotifier` | notifier.py | Telegram bot notifications |
| `WebhookNotifier` | notifier.py | Generic webhook notifications |

## IMPORT GRAPH

```
cli.py → fetcher, models, updater
updater → detector, fetcher, history, models, notifier, renderer
detector → history, models
fetcher → models
history → models
notifier → models
renderer → models
```

**Key constraint**: No circular dependencies — `updater.py` is the single orchestrator.

## CONVENTIONS (THIS MODULE)

- **ABC notifier**: `BaseNotifier` is abstract — all notifiers must implement `notify()` + `is_configured()`
- **Session reuse**: `FeedFetcher.session` is a cached property — never create sessions per-fetch
- **Atomic writes**: `HistoryManager` uses `tempfile.mkstemp` + `os.replace` for crash safety
- **Logging**: each module uses `logging.getLogger("rss_updater.{module}")` — never `logging.getLogger(__name__)`
- **No `from` re-exports**: `__init__.py` is intentionally empty — import from specific modules instead

## ANTI-PATTERNS (THIS MODULE)

- **DO NOT** call `requests.get()` directly — always go through `FeedFetcher`
- **DO NOT** modify history.json outside `HistoryManager`
- **DO NOT** add sync/async mixed notification dispatch — notifiers are async, called via `asyncio.run()`
- **DO NOT** import from `rss_updater/__init__.py` — it's empty by design
