# Checklist

## Phase 1: 基础设施与工具链

- [x] `rss_updater/` 包目录结构已创建，包含全部 10 个子模块
- [x] `tests/` 目录结构已创建，包含 `conftest.py` 和全部测试文件
- [x] `requirements.txt` 已更新，包含 pydantic、filelock、pytest、pytest-cov、ruff、mypy
- [x] `pyproject.toml` 已创建，ruff/pytest/mypy 配置正确
- [x] `rss_updater.py` 兼容入口文件已创建，可正常委托给新包

## Phase 2: 核心模块重构

- [x] Pydantic 模型 `Article`, `CheckResult`, `FeedConfig`, `Settings`, `NotificationChannel`, `AppConfig` 已定义并通过测试
- [x] 配置加载函数 `load_config` 能正确解析旧版 `rss_config.json` 并校验非法输入
- [x] 日志系统使用标准库 `logging`，支持控制台和文件双输出，支持 JSON 格式
- [x] `HistoryManager` 使用 `filelock.FileLock` 实现跨平台文件锁
- [x] `FeedFetcher` 类提取三级降级策略，支持策略注入和 mock 测试
- [x] `ContentChangeDetector` 保持 SHA-256 哈希逻辑，支持识别新增文章
- [x] `MarkdownRenderer` 支持自定义模板渲染，README 标记替换逻辑正确

## Phase 3: 通知系统与主控制器

- [x] `BaseNotifier` 抽象基类已定义，支持动态加载
- [x] `WebhookNotifier` 和 `TelegramNotifier` 已实现并通过测试
- [x] `BarkNotifier` 扩展示例已实现
- [x] `RSSUpdater` 主控制器能正确编排各模块
- [x] CLI 支持 `--config`, `--check-mode`, `--force`, `--verbose`, `--health-check`
- [x] `--health-check` 输出包含 RSS 源 HTTP 状态、响应时间、文章数量、错误信息

## Phase 4: CI/CD 与集成验证

- [x] `.github/workflows/lint-and-test.yml` 已创建，能正确运行 ruff + mypy + pytest
- [x] `.github/workflows/update-blog-posts.yml` 已重构，移除冗余 `git diff` 步骤
- [x] CI 缓存配置正确（pip + pytest）
- [x] 完整测试套件通过，核心模块覆盖率 ≥80%
- [x] 本地 `--check-mode` 运行结果与旧版行为一致
- [x] 本地 `--health-check` 运行正常，输出格式正确
