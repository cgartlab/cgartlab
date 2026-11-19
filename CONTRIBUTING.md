# 贡献指南

感谢贡献！本项目是 RSS 自动化流水线：按 `rss_config.json` 抓取源，生成并更新 README。

## 开发环境

- Python >= 3.11
- `pip install -r requirements.txt`
- 在仓库内建虚拟环境，**不要提交 `venv/`**（`.gitignore` 已覆盖）

## 代码规范

提 PR 前三者都要通过：

```bash
pytest
ruff check
mypy
```

## 提交规范

Conventional Commits：`feat` / `fix` / `docs` / `style` / `refactor` / `perf` / `test` / `chore` / `ci`

示例：`fix(rss): handle feeds without a title field`

## 提 PR 前

- 用真实 feed 端到端跑过一次
- 改动涉及源配置 → 同步 `rss_config.json`
- 依赖变更 → 同步 `requirements.txt` 与 `pyproject.toml`

## 安全问题

不要在公开 issue 报告漏洞，见 [SECURITY.md](SECURITY.md)。
