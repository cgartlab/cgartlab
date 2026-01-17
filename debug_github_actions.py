#!/usr/bin/env python3
"""
GitHub Actions调试脚本
帮助诊断GitHub Actions工作流的问题
"""

import subprocess
import sys
import os

def check_git_status():
    """检查Git状态"""
    print("🔍 检查Git状态...")
    
    try:
        # 检查当前分支
        result = subprocess.run(["git", "branch", "--show-current"], 
                              capture_output=True, text=True)
        current_branch = result.stdout.strip()
        print(f"✅ 当前分支: {current_branch}")
        
        # 检查远程仓库
        result = subprocess.run(["git", "remote", "-v"], 
                              capture_output=True, text=True)
        print(f"✅ 远程仓库:\n{result.stdout}")
        
        # 检查未提交的更改
        result = subprocess.run(["git", "status", "--porcelain"], 
                              capture_output=True, text=True)
        if result.stdout.strip():
            print("⚠️ 有未提交的更改:")
            print(result.stdout)
        else:
            print("✅ 没有未提交的更改")
            
        return True
        
    except Exception as e:
        print(f"❌ Git状态检查失败: {e}")
        return False

def check_github_workflow():
    """检查GitHub Actions工作流配置"""
    print("\n🔍 检查GitHub Actions工作流配置...")
    
    workflow_file = ".github/workflows/rss-update.yml"
    
    if not os.path.exists(workflow_file):
        print(f"❌ 工作流文件不存在: {workflow_file}")
        return False
    
    try:
        with open(workflow_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查关键配置
        checks = [
            ("schedule配置", "cron:" in content),
            ("workflow_dispatch", "workflow_dispatch" in content),
            ("Python设置", "setup-python" in content),
            ("依赖安装", "requirements.txt" in content),
            ("RSS更新器", "rss_updater.py" in content),
            ("提交推送", "git push" in content)
        ]
        
        all_passed = True
        for check_name, check_result in checks:
            if check_result:
                print(f"✅ {check_name}: 正常")
            else:
                print(f"❌ {check_name}: 缺失")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ 工作流配置检查失败: {e}")
        return False

def check_rss_config():
    """检查RSS配置"""
    print("\n🔍 检查RSS配置...")
    
    config_file = "rss_config.json"
    
    if not os.path.exists(config_file):
        print(f"❌ 配置文件不存在: {config_file}")
        return False
    
    try:
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if "feeds" in config and len(config["feeds"]) > 0:
            print(f"✅ RSS配置正常，有 {len(config['feeds'])} 个订阅源")
            for feed in config["feeds"]:
                print(f"   - {feed.get('name', '未知')}: {feed.get('url', '未知')}")
            return True
        else:
            print("❌ RSS配置中没有订阅源")
            return False
            
    except Exception as e:
        print(f"❌ RSS配置检查失败: {e}")
        return False

def check_github_actions_status():
    """检查GitHub Actions状态"""
    print("\n🔍 检查GitHub Actions状态...")
    
    try:
        # 获取最近的工作流运行
        result = subprocess.run(["git", "remote", "get-url", "origin"], 
                              capture_output=True, text=True)
        remote_url = result.stdout.strip()
        
        if "github.com" in remote_url:
            # 提取仓库信息
            import re
            match = re.search(r'github\.com[:/]([^/]+)/([^/\.]+)', remote_url)
            if match:
                owner, repo = match.groups()
                print(f"✅ GitHub仓库: {owner}/{repo}")
                print("\n📋 下一步操作:")
                print(f"1. 访问 https://github.com/{owner}/{repo}/actions")
                print("2. 检查 'RSS Auto Update' 工作流")
                print("3. 查看最近运行的日志")
                print("4. 如果没有运行，可以手动触发")
                return True
        
        print("⚠️ 无法确定GitHub仓库地址")
        print(f"远程地址: {remote_url}")
        return True
        
    except Exception as e:
        print(f"❌ GitHub Actions状态检查失败: {e}")
        return False

def main():
    """主调试函数"""
    print("=" * 60)
    print("GitHub Actions调试工具")
    print("=" * 60)
    
    # 检查当前目录是否为Git仓库
    if not os.path.exists(".git"):
        print("❌ 当前目录不是Git仓库")
        return
    
    # 执行各项检查
    checks = [
        ("Git状态检查", check_git_status),
        ("GitHub Actions配置检查", check_github_workflow),
        ("RSS配置检查", check_rss_config),
        ("GitHub Actions状态检查", check_github_actions_status)
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有基础检查通过")
        print("\n🔧 常见问题解决方案:")
        print("1. 确保GitHub仓库的Actions权限已开启")
        print("2. 检查GitHub仓库的Settings -> Actions -> General")
        print("3. 确保 'Workflow permissions' 设置为 'Read and write permissions'")
        print("4. 手动触发工作流测试")
    else:
        print("⚠️ 发现一些问题，请根据上面的提示进行修复")
    
    print("\n📋 手动测试步骤:")
    print("1. 运行: python rss_updater.py")
    print("2. 检查README.md是否被更新")
    print("3. 提交并推送到GitHub")
    print("4. 在GitHub上手动触发工作流")

if __name__ == "__main__":
    main()