# CGArtLab RSS Updater 优化与改进 Spec

## Why

当前 `cgartlab` 项目的 RSS 自动更新器已具备基础功能，但在代码质量、可维护性、健壮性和扩展性方面仍有明显短板：
- 单文件 824 行，职责混杂，难以测试和扩展
- 缺乏单元测试，变更风险高
- 日志和历史管理耦合过深，且 Windows 文件锁为简化实现
- 配置验证与业务逻辑混合
- 缺少类型安全（无 mypy/pyright）和代码风格统一（无 ruff/black）
- 通知系统仅支持 Webhook/Telegram，扩展困难
- GitHub Actions 工作流在 `--check-mode` 后直接 `git diff`，存在逻辑冗余

## What Changes

- **BREAKING** 将 `rss_updater.py` 拆分为模块化包结构（`rss_updater/`）
- **BREAKING** 引入 `pydantic` 进行配置和数据模型校验，替换手写验证逻辑
- 引入 `pytest` + `pytest-cov` 构建完整单元测试体系
- 引入 `ruff` 统一代码风格与 lint，引入 `mypy` 进行静态类型检查
- 重构日志系统：解耦 `RSSLogger` 与 `HistoryManager`，支持结构化日志（JSON）
- 实现真正的跨平台文件锁（`filelock` 库）
- 扩展通知系统插件架构，支持 Bark/Discord/企业微信等渠道
- 优化 GitHub Actions 工作流：简化步骤、增强缓存、添加测试步骤
- 添加 CLI 健康检查命令 `--health-check`
- 添加 RSS 源可用性监控与统计报告

## Impact

- Affected specs: 配置校验、RSS 获取、变更检测、通知推送、CI/CD
- Affected code: `rss_updater.py` → `rss_updater/` 包, `rss_config.json` 结构兼容升级, `.github/workflows/update-blog-posts.yml`

## ADDED Requirements

### Requirement: 模块化架构
The system SHALL 将原有单文件脚本重构为 `rss_updater/` Python 包，包含以下子模块：
- `models.py` — Pydantic 数据模型（Article, CheckResult, Config）
- `fetcher.py` — RSS 获取策略（直连/代理/feedparser）
- `detector.py` — 内容变更检测
- `history.py` — 历史记录管理
- `notifier.py` — 通知系统（含插件基类）
- `renderer.py` — Markdown 生成
- `updater.py` — 主控制器
- `cli.py` — 命令行入口
- `logger.py` — 日志配置

#### Scenario: 成功导入
- **WHEN** 用户执行 `python -m rss_updater --help`
- **THEN** 程序正常输出帮助信息，无导入错误

### Requirement: 配置与数据模型校验
The system SHALL 使用 Pydantic v2 定义所有配置和数据模型，运行时自动校验类型与约束。

#### Scenario: 配置非法
- **WHEN** `rss_config.json` 中 `feeds[].max_posts` 为负数
- **THEN** 程序启动时立即抛出验证错误，并输出人类可读的错误信息

### Requirement: 单元测试覆盖
The system SHALL 为核心模块提供 ≥80% 的单元测试覆盖率。

#### Scenario: 运行测试
- **WHEN** 执行 `pytest tests/ --cov=rss_updater --cov-report=term-missing`
- **THEN** 所有测试通过，且覆盖率报告显示核心模块 ≥80%

### Requirement: 代码质量工具链
The system SHALL 集成 `ruff`（format + lint）和 `mypy`（type check），并在 CI 中强制执行。

#### Scenario: CI 检查
- **WHEN** PR 中引入类型错误或风格违规
- **THEN** GitHub Actions 的 `lint-and-test` job 失败，阻止合并

### Requirement: 跨平台文件锁
The system SHALL 使用 `filelock` 库替代当前平台判断逻辑，实现可靠的跨平台文件锁。

#### Scenario: 并发写入历史
- **WHEN** 两个进程同时尝试写入 `check_history.json`
- **THEN** 只有一个进程成功获取锁，另一个阻塞等待，避免数据损坏

### Requirement: 通知插件架构
The system SHALL 定义 `BaseNotifier` 抽象基类，允许通过配置动态加载通知渠道。

#### Scenario: 添加 Bark 通知
- **WHEN** 在 `rss_config.json` 的 `notifications.channels` 中添加 `{"type": "bark", "key": "xxx"}`
- **THEN** 新文章发布时，系统自动推送 Bark 通知，无需修改核心代码

### Requirement: CLI 健康检查
The system SHALL 提供 `--health-check` 命令，检查所有配置 RSS 源的可访问性并输出报告。

#### Scenario: 健康检查
- **WHEN** 执行 `python -m rss_updater --health-check`
- **THEN** 输出每个 RSS 源的 HTTP 状态、响应时间、文章数量、错误信息（如有）

### Requirement: CI/CD 优化
The system SHALL 优化 GitHub Actions 工作流：
- 分离 `lint-and-test` 与 `update-blog-posts` 两个工作流
- `update-blog-posts` 使用 `--check-mode` 后，直接根据脚本退出码和输出判断，不再额外 `git diff`
- 添加 `actions/cache` 缓存 pip 和 pytest 依赖
- 添加工作流运行结果摘要（成功/失败/无变化）

## MODIFIED Requirements

### Requirement: RSS 获取策略
现有三级降级策略（直连 → Jina AI 代理 → feedparser 直连）保持不变，但 SHALL 提取为独立 `FeedFetcher` 类，支持策略注入和单元测试 mock。

### Requirement: README 标记替换
现有 HTML 注释标记替换逻辑保持不变，但 SHALL 移至 `renderer.py`，支持自定义模板渲染。

## REMOVED Requirements

### Requirement: 手写配置验证
**Reason**: 由 Pydantic 模型自动替代
**Migration**: 删除 `_validate_config` 方法，Pydantic 会在模型初始化时自动校验

### Requirement: 单文件脚本结构
**Reason**: 不符合可维护性和可测试性要求
**Migration**: `rss_updater.py` 保留为兼容入口（导入并委托给包），新开发全部在 `rss_updater/` 包中进行
