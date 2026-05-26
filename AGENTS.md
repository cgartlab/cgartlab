# AGENTS.md — cgartlab

**分层**: 个人品牌 (Personal Brand) — 内容自动化
**Updated:** 2026-05-25

## 用途

个人博客站点 RSS 自动化工具。自动抓取博客文章更新 README.md，是 cgartlab.github.io（主站）内容流水线的一部分。

## 开发命令

```bash
# 运行 RSS 更新器（检测到新内容才更新 README.md）
python rss_updater.py

# 检查模式：只检测变化，不更新文件
python rss_updater.py --check-mode

# 强制更新：无论是否有变化都更新
python rss_updater.py --force

# 详细输出
python rss_updater.py --verbose
```

## 配置

编辑 `rss_config.json`：

| 字段 | 说明 |
|------|------|
| `feeds[].url` | RSS 订阅源 URL |
| `feeds[].section_marker` | README 中的 HTML 注释标记（如 `BLOG_POSTS_START`） |
| `feeds[].max_posts` | 显示的文章数量 |
| `feeds[].enabled` | 启用/禁用该订阅源 |

更新器替换 `<!-- {section_marker} -->` 和 `<!-- {section_marker.replace('START', 'END')} -->` 之间的内容。

## 技术细节

- **Python 版本**：3.11（见 `.github/workflows/update-blog-posts.yml`）
- **依赖**：`feedparser==6.0.11`, `requests==2.32.3`, `urllib3>=2.6.0,<3.0.0`
- **RSS 获取策略**：先直连，失败则用 `https://r.jina.ai/{url}` 代理，最后尝试 feedparser 直连
- **模块化重构**：核心功能已拆分为 `rss_fetcher.py` / `rss_parser.py` / `readme_updater.py` 模块
- **历史缓存**：`.rss_history/` 目录保留检查历史和工作日志
- **CODE_WIKI.md** — 项目代码百科，位于根目录，详细说明架构和核心逻辑

## GitHub Workflow

- 每 4 小时定时运行
- 推送到 main 且变更 `rss_config.json`、`rss_updater.py` 或 workflow 文件时触发
- 支持手动 `workflow_dispatch`，可选 `force_update` 参数

工作流流程：
1. `--check-mode` 检测变化
2. 检查 `NEW_CONTENT_DETECTED=true` 或 `CONTENT_UPDATED=true` 输出
3. 有变化则提交 README.md