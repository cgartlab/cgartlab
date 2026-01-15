#!/usr/bin/env python3
"""
测试GitHub Actions环境的脚本
"""

import sys
import os
import json

def test_environment():
    """测试环境变量和依赖"""
    print("=== 测试GitHub Actions环境 ===")
    
    # 测试Python版本
    print(f"Python版本: {sys.version}")
    
    # 测试当前目录
    print(f"当前目录: {os.getcwd()}")
    
    # 测试文件是否存在
    files_to_check = [
        'blog_config.json',
        'scripts/fetch_blog_posts.py',
        'scripts/update_readme.py'
    ]
    
    for file_path in files_to_check:
        exists = os.path.exists(file_path)
        print(f"文件 {file_path}: {'存在' if exists else '不存在'}")
    
    # 测试配置文件读取
    try:
        with open('blog_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            print(f"配置文件读取成功: {config}")
    except Exception as e:
        print(f"配置文件读取失败: {e}")
    
    # 测试依赖包
    try:
        import requests
        print("✅ requests 包可用")
    except ImportError:
        print("❌ requests 包不可用")
    
    try:
        import feedparser
        print("✅ feedparser 包可用")
    except ImportError:
        print("❌ feedparser 包不可用")
    
    print("=== 环境测试完成 ===")

if __name__ == "__main__":
    test_environment()