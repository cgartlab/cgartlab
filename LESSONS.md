# LESSONS — cgartlab

> 个人博客 RSS 自动化工具：Python 3.11 + feedparser，定时抓取博客并回写 `README.md` 的标记区块。
> 本仓库从真实失误沉淀的「教训→规则」清单。**会话开始先全文阅读并遵循其中所有规则**；出现新失误按 §维护 追加。
> 权威依据：Anthropic Claude Code memory/best practices（<200 行、具体可验证、第二次犯同样错即写入）；社区 lessons.md 惯例（Boris Cherny，Anthropic）。
> 来源：本仓库 AGENTS.md 的 gotchas/quirks + 已验证 fix 提交；预填为种子，后续由 Agent 在真实工作中增长。

## 维护
- **触发**：用户纠正 / Agent 自查到的失误 / 非显而易见的 gotcha。
- **格式**：`### <主题>` 下，每条 = 失误（具体场景）→ 规则（最小可执行指令），一行可验证。
- **只记项目特有、不可从代码推断的**；通用最佳实践不写；含糊措辞（"小心""注意"）删掉。
- **重复出现** → 升级进 `AGENTS.md` 硬规则；**月度审阅**裁剪过期项；目标 < 200 行。

## RSS 与 README 标记

### 标记区块
- 失误：README 的 `<!-- BLOG_POSTS_START -->` 与 END 标记不匹配，内容写入失败 → 规则：END 标记由 `marker.replace('START','END')` 推导，改 marker 必须成对改（见 AGENTS.md「配置」）
- 失误：renderer 写错 END 标记，博客区内容被截断 → 规则：改 renderer 后必须验证 END 标记确实存在（commit e7682a9）

### 获取策略
- 失误：RSS 源直连返回 403，脚本报错退出 → 规则：获取固定三级：直连 → `https://r.jina.ai/{url}` 代理 → feedparser 直连，不要只试直连（见 AGENTS.md「技术细节」）
- 失误：无效 RSS 源让整个更新流程崩掉 → 规则：新增 feed 前先验证可达；单源失败要降级而不是崩整批（commit f8c71a0）

### 代码分层
- 失误：直接把逻辑塞进 `rss_updater.py` → 规则：入口现为 6 行薄封装，仅委托 `rss_updater.cli.main`；业务逻辑改到 `rss_updater/` 包内模块（见 AGENTS.md「技术细节」）
- 失误：日志级别硬编码，配置改不动 → 规则：logger 必须读取配置中的级别（commit 6400843）

## 构建与部署

### CI 与 workflow
- 失误：CI 步骤带 `--check-mode`，README 永远不被写入 → 规则：需要写文件的 CI 步骤不得带 `--check-mode`（commit 792ec3f）
- 失误：无变化时也提交 README，产生噪声 commit → 规则：默认只在检测到新内容时更新；无条件更新用 `--force`（commit 87404b2）
- 失误：GitHub Actions 里写了 `workflows`/`statuses` write 权限 → 规则：`GITHUB_TOKEN` permissions 只能填 GitHub 允许的字段（commit 7ccac86）

### 提交卫生
- 失误：CRLF 损坏入库 → 规则：Windows 侧提交要显式配置 git identity 与行尾（commit 35b3722）
- 失误：AI 工具产物（`.trae/` 等）被提交 → 规则：提交前清理 AI 工具产物目录（commit e7682a9）
- 失误：未使用的循环变量触发 ruff B007 → 规则：lint 报错要改代码而不是忽略规则（commit 1aa9eeb）
