# AGENTS.md — cgartlab

**Generated:** 2026-05-25 17:02
**Commit:** `d9aa7c2`
**Branch:** `main`
**分层**: 个人品牌 (Personal Brand) — 内容自动化

## OVERVIEW

个人博客站点 RSS 自动化工具。自动抓取博客文章更新 README.md，是 cgartlab.github.io（主站）内容流水线的一部分。

**Stack:** Python 3.11, feedparser, requests, pydantic, pytest, ruff, mypy

## STRUCTURE

```
cgartlab/
├── rss_updater/         # 核心包：10 个模块，~830 行
│   ├── cli.py           # 参数解析 + 入口
│   ├── models.py        # Pydantic 数据模型 + 配置加载
│   ├── fetcher.py       # RSS 请求 + 响应解析
│   ├── detector.py      # 内容变更检测
│   ├── updater.py       # 主流程编排
│   ├── renderer.py      # Markdown 渲染
│   ├── history.py       # 历史记录（JSON + filelock）
│   ├── notifier.py      # 通知（Webhook/Telegram）
│   └── logger.py        # JSON 日志格式化
├── tests/               # 测试包：~1415 行，镜像模块结构
├── .github/workflows/   # CI: lint-and-test + update-blog-posts
└── rss_updater.py       # 兼容入口 → cli.main()
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| Entry point, CLI args | `rss_updater/cli.py` | `main()` |
| Data models, config loading | `rss_updater/models.py` | Pydantic v2 |
| RSS fetching logic | `rss_updater/fetcher.py` | 3-strategy fallback |
| Change detection | `rss_updater/detector.py` | SHA-256 hash compare |
| Main update orchestration | `rss_updater/updater.py` | `RSSUpdater` class |
| History persistence | `rss_updater/history.py` | JSON + filelock |
| Markdown section replacement | `rss_updater/renderer.py` | regex-based |
| Notification dispatching | `rss_updater/notifier.py` | Webhook + Telegram |
| Logging setup | `rss_updater/logger.py` | JSON file + console |
| Config schema | `rss_config.json` | per-feed `section_marker` |
| CI pipeline definition | `.github/workflows/` | lint-and-test + deploy |

## CONVENTIONS

- **Type hints**: `from __future__ import annotations` on all modules
- **Strict mypy**: `strict = true` in `pyproject.toml`; `# type: ignore[code]` only where necessary
- **Ruff linter**: line-length 120, target py311, selects E/F/I/W/UP/B/C4/SIM
- **Pydantic v2**: models use `BaseModel`, `Field`, `field_validator`, `ConfigDict`. No `model_` prefix on v1 methods.
- **Logging**: module-level `logger = logging.getLogger("rss_updater.{module}")`
- **Test naming**: `tests/test_{module}.py` mirrors `rss_updater/{module}.py`
- **No `__init__` exports**: `rss_updater/__init__.py` is empty (flat import inside package)
- **UTF-8**: explicit encoding on all file I/O (`encoding="utf-8"`)
- **Path handling**: `pathlib.Path` preferred over `os.path`

## ANTI-PATTERNS

- **DO NOT** use `as any` / `# type: ignore` without specific error code
- **DO NOT** modify `README.md`'s section markers (`<!-- BLOG_POSTS_START/END -->`)
- **DO NOT** commit `.rss_history/` changes manually — CI manages it
- **DO NOT** add new dependencies without adding to `requirements.txt` AND CI install step
- **DO NOT** bypass change detection unless `--force` is explicitly passed

## COMMANDS

```bash
# 运行 RSS 更新器（检测到新内容才更新 README.md）
python rss_updater.py

# 检查模式：只检测变化，不更新文件
python rss_updater.py --check-mode

# 强制更新：无论是否有变化都更新
python rss_updater.py --force

# 详细输出
python rss_updater.py --verbose

# 健康检查
python rss_updater.py --health-check

# Lint + format + type check + test
ruff check rss_updater/ tests/
ruff format --check rss_updater/ tests/
mypy rss_updater/
pytest tests/ --cov=rss_updater --cov-report=term
```

## CONFIG

编辑 `rss_config.json`：

| 字段 | 说明 |
|------|------|
| `feeds[].url` | RSS 订阅源 URL |
| `feeds[].section_marker` | README 中的 HTML 注释标记（如 `BLOG_POSTS_START`） |
| `feeds[].max_posts` | 显示的文章数量 |
| `feeds[].enabled` | 启用/禁用该订阅源 |

更新器替换 `<!-- {section_marker} -->` 和 `<!-- {section_marker.replace('START', 'END')} -->` 之间的内容。

## NOTES

- **RSS fallback chain**: direct GET → `r.jina.ai` proxy → feedparser direct
- **3.11+ only**: `datetime.UTC`, `list[Article]` syntax, `str | None` unions
- **CI cache**: pip + `.rss_history` both cached in GitHub Actions (separate keys)
- **history.json**: uses atomic file writes (tempfile + os.replace) + FileLock
- **Notification typing**: `NotificationChannel` has `model_config = ConfigDict(extra="allow")` for heterogeneous channel configs