# 📝 博客文章列表设置指南

## 概述

这个功能会自动在你的GitHub个人主页显示最新的博客文章列表，支持实时更新。

## 快速开始

### 1. 配置博客订阅源

编辑 `blog_config.json` 文件，添加你的博客RSS/Atom订阅源：

```json
{
  "blog_feeds": [
    {
      "name": "我的技术博客",
      "url": "https://your-blog.com/feed",
      "type": "rss"
    }
  ],
  "max_posts": 5,
  "update_interval_hours": 24
}
```

### 2. 手动测试

运行以下命令测试功能：

```bash
# 安装依赖
pip install feedparser requests

# 获取博客文章
python scripts/fetch_blog_posts.py

# 更新README
python scripts/update_readme.py
```

### 3. 提交更改

```bash
git add .
git commit -m "添加博客文章列表功能"
git push
```

## 支持的博客平台

- **WordPress**: `https://your-site.com/feed/`
- **Medium**: `https://medium.com/feed/@your-username`
- **GitHub Pages**: `https://username.github.io/feed.xml`
- **Hugo**: `https://your-site.com/index.xml`
- **Jekyll**: `https://your-site.com/feed.xml`
- **自定义RSS/Atom**: 任何标准的RSS或Atom订阅源

## 自动更新

GitHub Actions会自动：
- 每天凌晨2点（UTC）更新文章列表
- 当脚本文件有更改时自动运行
- 支持手动触发更新

## 手动触发更新

1. 进入GitHub仓库的 **Actions** 标签页
2. 选择 **Update Blog Posts** 工作流
3. 点击 **Run workflow** 按钮

## 自定义样式

编辑 `scripts/fetch_blog_posts.py` 中的 `generate_markdown()` 函数来自定义显示格式。

## 故障排除

### 常见问题

1. **无法获取文章**
   - 检查订阅源URL是否正确
   - 确认订阅源是否公开可访问
   - 查看GitHub Actions日志获取详细错误信息

2. **更新不生效**
   - 确保GitHub Actions有权限提交更改
   - 检查工作流是否成功运行

3. **格式显示问题**
   - 检查Markdown语法是否正确
   - 确保特殊字符已正确转义

### 调试模式

在本地运行调试：

```bash
python scripts/fetch_blog_posts.py --debug
```

## 高级配置

### 多博客源
支持同时从多个博客获取文章：

```json
{
  "blog_feeds": [
    {
      "name": "技术博客",
      "url": "https://tech-blog.com/feed"
    },
    {
      "name": "设计博客", 
      "url": "https://design-blog.com/rss"
    }
  ]
}
```

### 自定义更新频率
编辑 `.github/workflows/update-blog-posts.yml` 中的cron表达式：

```yaml
schedule:
  # 每6小时更新一次
  - cron: '0 */6 * * *'
```

## 技术支持

如有问题，请检查：
1. GitHub Actions运行日志
2. Python脚本输出信息
3. 订阅源URL是否可访问