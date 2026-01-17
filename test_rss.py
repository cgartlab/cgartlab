#!/usr/bin/env python3
"""
RSS更新器测试脚本
用于本地测试RSS功能
"""

import subprocess
import sys
import os

def test_rss_updater():
    """测试RSS更新器"""
    print("🧪 开始测试RSS更新器...")
    
    # 检查Python环境
    try:
        result = subprocess.run([sys.executable, "--version"], 
                              capture_output=True, text=True)
        print(f"✅ Python版本: {result.stdout.strip()}")
    except Exception as e:
        print(f"❌ Python环境检查失败: {e}")
        return False
    
    # 安装依赖
    print("📦 安装依赖包...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True)
        print("✅ 依赖安装成功")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        return False
    
    # 运行RSS更新器
    print("🚀 运行RSS更新器...")
    try:
        result = subprocess.run([sys.executable, "rss_updater.py"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ RSS更新器运行成功")
            print("输出信息:")
            print(result.stdout)
            
            # 检查README是否被更新
            if os.path.exists("README.md"):
                with open("README.md", "r", encoding="utf-8") as f:
                    content = f.read()
                    if "Last Updated:" in content:
                        print("✅ README文件已成功更新")
                        return True
                    else:
                        print("❌ README文件未正确更新")
                        return False
            else:
                print("❌ README文件不存在")
                return False
                
        else:
            print(f"❌ RSS更新器运行失败，返回码: {result.returncode}")
            print("错误输出:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ 运行RSS更新器时出错: {e}")
        return False

def check_config():
    """检查配置文件"""
    print("\n🔧 检查配置文件...")
    
    config_files = ["rss_config.json", "requirements.txt"]
    
    for file in config_files:
        if os.path.exists(file):
            print(f"✅ {file} 存在")
        else:
            print(f"❌ {file} 不存在")
            return False
    
    return True

def main():
    """主测试函数"""
    # 设置编码以确保在Windows下正常显示
    import sys
    import io
    
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 50)
    print("RSS自动化工作流测试")
    print("=" * 50)
    
    # 检查配置文件
    if not check_config():
        print("\n配置文件检查失败，测试中止")
        sys.exit(1)
    
    # 测试RSS更新器
    if test_rss_updater():
        print("\n所有测试通过! RSS自动化工作流可以正常工作")
        print("\n下一步:")
        print("1. 将代码推送到GitHub仓库")
        print("2. GitHub Actions会自动在每天5点运行")
        print("3. 你也可以手动在GitHub上触发工作流")
    else:
        print("\n测试失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()