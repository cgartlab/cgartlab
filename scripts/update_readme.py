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
        print("BLOG_POSTS.md 文件不存在，请先运行 fetch_blog_posts.py")
        return False
    
    with open(blog_file, 'r', encoding='utf-8') as f:
        blog_content = f.read()
    
    # 读取README.md
    readme_file = os.path.join(os.path.dirname(__file__), '..', 'README.md')
    with open(readme_file, 'r', encoding='utf-8') as f:
        readme_content = f.read()
    
    # 替换博客文章部分
    pattern = r'<!-- BLOG_POSTS_START -->.*?<!-- BLOG_POSTS_END -->'
    replacement = f'<!-- BLOG_POSTS_START -->\n{blog_content}\n<!-- BLOG_POSTS_END -->'
    
    updated_content = re.sub(pattern, replacement, readme_content, flags=re.DOTALL)
    
    # 写回README.md
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print("README.md 已更新")
    return True


if __name__ == "__main__":
    update_readme_with_blog_posts()