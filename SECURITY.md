# Security Policy

## 报告漏洞

请不要在公开的 issue 中报告安全问题。请使用 GitHub 的私密漏洞报告：

1. 进入仓库 **Security** 标签页
2. 点击 **Report a vulnerability**
3. 提供复现步骤与影响范围

我会在 7 天内确认收到。

## 支持范围

仅支持 `main` 最近一个版本。

## 本项目的敏感面

`cgartlab` 按 `rss_config.json` 抓取外部 RSS feed 并生成 README。请特别留意：

- **URL 拉取 / SSRF** — 源地址由配置文件指定。不要把指向内网地址的源写入配置。
- **Markdown 注入** — feed 标题与摘要会进入生成的 README，由 GitHub 渲染。恶意 feed 可能注入链接、图片或标记。
- **Actions secrets** — 工作流不应打印 token。
- **`venv/` 不要提交** — `.gitignore` 已覆盖，但不要绕过。
