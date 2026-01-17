# RSS自动化工作流使用指南

## 概述

这是一个轻量化的RSS自动化工作流系统，用于自动检查网站更新并更新README.md文档。

## 文件结构

```
├── rss_updater.py          # 主脚本，处理RSS订阅和README更新
├── rss_config.json         # RSS订阅源配置文件
├── requirements.txt        # Python依赖包列表
├── test_rss.py            # 本地测试脚本
├── .github/workflows/     # GitHub Actions工作流
│   └── rss-update.yml     # 自动化工作流配置
└── README.md              # 目标更新文件
```

## 快速开始

### 1. 本地测试

在本地运行测试脚本，确保一切正常：

```bash
python test_rss.py
```

### 2. 手动运行RSS更新器

```bash
python rss_updater.py
```

### 3. 推送到GitHub

将代码推送到GitHub仓库后，GitHub Actions会自动在每天5点（UTC时间）运行。

## 配置扩展

### 添加新的RSS订阅源

编辑 `rss_config.json` 文件，在 `feeds` 数组中添加新的订阅源：

```json
{
  "feeds": [
    {
      "name": "CGArtLab Blog",
      "url": "https://cgartlab.com/feed.xml",
      "section_marker": "BLOG_POSTS_START",
      "max_posts": 5
    },
    {
      "name": "另一个博客",
      "url": "https://example.com/feed.xml",
      "section_marker": "OTHER_BLOG_START",
      "max_posts": 3
    }
  ]
}
```

### 在README中添加新的内容区域

在README.md中添加对应的标记：

```markdown
<!-- OTHER_BLOG_START -->
<!-- OTHER_BLOG_END -->
```

RSS更新器会自动识别这些标记并更新其中的内容。

## 自定义配置选项

### RSS源配置参数

- `name`: 订阅源的名称（用于日志显示）
- `url`: RSS订阅链接
- `section_marker`: README中对应区域的开始标记
- `max_posts`: 显示的最大文章数量

### 修改运行时间

编辑 `.github/workflows/rss-update.yml` 文件中的cron表达式：

```yaml
schedule:
  # 每天早上5点运行 (UTC时间，对应北京时间13点)
  - cron: '0 21 * * *'
```

Cron表达式格式：`分钟 小时 日 月 星期`

## 故障排除

### 常见问题

1. **RSS订阅无法解析**
   - 检查RSS链接是否正确
   - 确认网站是否提供RSS订阅
   - 尝试使用其他RSS阅读器验证

2. **GitHub Actions运行失败**
   - 检查仓库的Actions权限设置
   - 确认 `GITHUB_TOKEN` 有写入权限
   - 查看Actions日志获取详细错误信息

3. **本地测试失败**
   - 确保Python 3.7+已安装
   - 运行 `pip install -r requirements.txt` 安装依赖
   - 检查网络连接

### 日志输出

脚本会输出详细的日志信息，帮助诊断问题：

- ✅ 成功操作
- ⚠️ 警告信息
- ❌ 错误信息

## 技术细节

### 依赖包

- `feedparser`: RSS/Atom订阅解析
- `requests`: HTTP请求库

### 支持的RSS格式

- RSS 2.0
- Atom 1.0
- 大多数常见的RSS变体

## 贡献

欢迎提交问题和改进建议！

## 许可证

MIT License
