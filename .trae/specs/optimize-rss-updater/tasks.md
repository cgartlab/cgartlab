# Tasks

## Phase 1: 基础设施与工具链

- [x] Task 1: 初始化项目结构与依赖管理
  - [x] SubTask 1.1: 创建 `rss_updater/` 包目录结构（`__init__.py`, `models.py`, `fetcher.py`, `detector.py`, `history.py`, `notifier.py`, `renderer.py`, `updater.py`, `cli.py`, `logger.py`）
  - [x] SubTask 1.2: 创建 `tests/` 目录结构（`__init__.py`, `conftest.py`, `test_models.py`, `test_fetcher.py`, `test_detector.py`, `test_history.py`, `test_notifier.py`, `test_renderer.py`, `test_updater.py`）
  - [x] SubTask 1.3: 更新 `requirements.txt`，添加 `pydantic>=2.0`, `filelock>=3.0`, `pytest>=8.0`, `pytest-cov>=5.0`, `ruff>=0.6`, `mypy>=1.10`
  - [x] SubTask 1.4: 创建 `pyproject.toml`，配置 ruff、pytest、mypy 工具
  - [x] SubTask 1.5: 创建 `rss_updater.py` 兼容入口文件（导入并委托给 `rss_updater.cli:main`）

- [x] Task 2: Pydantic 数据模型与配置校验
  - [x] SubTask 2.1: 在 `rss_updater/models.py` 中定义 `Article`, `CheckResult`, `FeedConfig`, `Settings`, `NotificationChannel`, `AppConfig` Pydantic 模型
  - [x] SubTask 2.2: 实现配置加载函数 `load_config(path: str) -> AppConfig`
  - [x] SubTask 2.3: 编写 `test_models.py` 验证模型序列化/反序列化、非法输入校验

## Phase 2: 核心模块重构

- [x] Task 3: 日志系统重构
  - [x] SubTask 3.1: 在 `rss_updater/logger.py` 中实现 `setup_logging(log_dir: Path, level: str, json_format: bool = False)`
  - [x] SubTask 3.2: 使用标准库 `logging.getLogger("rss_updater")` 替代自定义 `RSSLogger` 类
  - [x] SubTask 3.3: 编写 `test_logger.py` 验证日志配置

- [x] Task 4: 跨平台文件锁与历史管理
  - [x] SubTask 4.1: 在 `rss_updater/history.py` 中使用 `filelock.FileLock` 替代平台判断逻辑
  - [x] SubTask 4.2: 重构 `HistoryManager` 类，解耦日志依赖，使用模块级 logger
  - [x] SubTask 4.3: 编写 `test_history.py` 测试并发写入、历史清理、哈希读写

- [x] Task 5: RSS 获取器重构
  - [x] SubTask 5.1: 在 `rss_updater/fetcher.py` 中定义 `FeedFetcher` 类，提取三级降级策略为独立方法
  - [x] SubTask 5.2: 支持策略注入（允许单元测试 mock session/response）
  - [x] SubTask 5.3: 编写 `test_fetcher.py`，使用 `responses` 或 `unittest.mock` mock HTTP 请求

- [x] Task 6: 变更检测与 Markdown 渲染
  - [x] SubTask 6.1: 在 `rss_updater/detector.py` 中实现 `ContentChangeDetector`，保持 SHA-256 哈希逻辑
  - [x] SubTask 6.2: 在 `rss_updater/renderer.py` 中实现 `MarkdownRenderer`，支持自定义模板
  - [x] SubTask 6.3: 编写 `test_detector.py` 和 `test_renderer.py`

## Phase 3: 通知系统与主控制器

- [x] Task 7: 通知插件架构
  - [x] SubTask 7.1: 在 `rss_updater/notifier.py` 中定义 `BaseNotifier` 抽象基类（`abc.ABC`）
  - [x] SubTask 7.2: 实现 `WebhookNotifier`, `TelegramNotifier` 作为内置插件
  - [x] SubTask 7.3: 实现 `BarkNotifier` 作为扩展示例
  - [x] SubTask 7.4: 编写 `test_notifier.py` 使用 `responses` mock 各通知渠道

- [x] Task 8: 主控制器与 CLI
  - [x] SubTask 8.1: 在 `rss_updater/updater.py` 中实现 `RSSUpdater` 主控制器，编排各模块
  - [x] SubTask 8.2: 在 `rss_updater/cli.py` 中实现 CLI（`argparse`），支持 `--config`, `--check-mode`, `--force`, `--verbose`, `--health-check`
  - [x] SubTask 8.3: 实现 `--health-check` 命令，输出 RSS 源可用性表格
  - [x] SubTask 8.4: 编写 `test_updater.py` 和 `test_cli.py`

## Phase 4: CI/CD 与集成验证

- [x] Task 9: GitHub Actions 工作流优化
  - [x] SubTask 9.1: 创建 `.github/workflows/lint-and-test.yml`，运行 ruff + mypy + pytest
  - [x] SubTask 9.2: 重构 `.github/workflows/update-blog-posts.yml`：
    - 移除冗余 `git diff` 步骤，直接根据脚本输出判断
    - 增强 `actions/cache` 配置（pip + pytest）
    - 添加工作流摘要输出
  - [x] SubTask 9.3: 验证工作流 YAML 语法（使用 `actionlint` 或本地检查）

- [x] Task 10: 集成测试与回归验证
  - [x] SubTask 10.1: 运行完整测试套件 `pytest tests/ --cov=rss_updater --cov-report=term-missing`
  - [x] SubTask 10.2: 确保核心模块覆盖率 ≥80%
  - [x] SubTask 10.3: 本地运行 `python rss_updater.py --check-mode` 验证与旧行为一致
  - [x] SubTask 10.4: 本地运行 `python rss_updater.py --health-check` 验证新功能

# Task Dependencies

- Task 2 依赖 Task 1
- Task 3 依赖 Task 1
- Task 4 依赖 Task 3
- Task 5 依赖 Task 2
- Task 6 依赖 Task 2
- Task 7 依赖 Task 2
- Task 8 依赖 Task 4, Task 5, Task 6, Task 7
- Task 9 依赖 Task 8
- Task 10 依赖 Task 9
