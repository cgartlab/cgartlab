#!/usr/bin/env python3
"""
更新README.md文件中的博客文章列表
"""

import os
import re


def update_readme_with_blog_posts():
    """将博客文章内容插入到README.md中"""
    
    # 读取博客文章内容
    blog_file = os.path.join(os.path.dirname(__file__), '..', 'BLOG_POSTS.md')
    if not os.path.exists(blog_file):
        print(f"[update_readme] 错误: BLOG_POSTS.md 文件不存在: {blog_file}")
        print("[update_readme] 请先运行 fetch_blog_posts.py")
        return False
    
    with open(blog_file, 'r', encoding='utf-8') as f:
        blog_content = f.read()
    
    print(f"[update_readme] 成功读取 BLOG_POSTS.md，内容长度: {len(blog_content)}")
    print(f"[update_readme] 博客文章内容预览:\n{blog_content[:200]}...")
    
    # 读取README.md
    readme_file = os.path.join(os.path.dirname(__file__), '..', 'README.md')
    with open(readme_file, 'r', encoding='utf-8') as f:
        readme_content = f.read()
    
    # 替换博客文章部分 - 更准确的正则表达式
    pattern = r'<!-- BLOG_POSTS_START -->.*?<!-- BLOG_POSTS_END -->'
    if not re.search(pattern, readme_content, flags=re.DOTALL):
        print("[update_readme] 错误: 未找到 BLOG_POSTS 标记")
        return False
    
    replacement = f'<!-- BLOG_POSTS_START -->\n{blog_content}\n<!-- BLOG_POSTS_END -->'
    
    updated_content = re.sub(pattern, replacement, readme_content, flags=re.DOTALL)
    
    # 写回README.md
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"[update_readme] README.md 已成功更新")
    print(f"[update_readme] 更新后文件大小: {len(updated_content)} 字符")
    return True


if __name__ == "__main__":
    success = update_readme_with_blog_posts()
    if success:
        print("[update_readme] ✅ 更新成功")
    else:
        print("[update_readme] ❌ 更新失败")
        exit(1)