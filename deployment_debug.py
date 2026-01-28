#!/usr/bin/env python3
"""
PythonAnywhere部署问题排查脚本
运行此脚本来诊断常见的部署问题
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_python_version():
    """检查Python版本"""
    print("=== Python版本检查 ===")
    print(f"Python版本: {sys.version}")
    print(f"Python路径: {sys.executable}")
    print()

def check_dependencies():
    """检查依赖包"""
    print("=== 依赖包检查 ===")
    try:
        import pip
        print("pip可用")
        
        # 检查requirements.txt
        if os.path.exists('requirements.txt'):
            print("找到requirements.txt文件")
            with open('requirements.txt', 'r') as f:
                packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                print(f"需要安装的包数量: {len(packages)}")
                for pkg in packages[:5]:  # 只显示前5个
                    print(f"  - {pkg}")
                if len(packages) > 5:
                    print(f"  ... 还有{len(packages)-5}个包")
        else:
            print("警告: 未找到requirements.txt文件")
        
        # 检查已安装的包
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            installed_packages = len(result.stdout.split('\n')) - 2
            print(f"已安装包数量: {installed_packages}")
    except Exception as e:
        print(f"依赖检查失败: {e}")
    print()

def check_file_structure():
    """检查文件结构"""
    print("=== 文件结构检查 ===")
    required_files = [
        'wsgi.py',
        'manage.py' if os.path.exists('manage.py') else None,
        'app.py',
        'requirements.txt'
    ]
    
    for file in required_files:
        if file and os.path.exists(file):
            print(f"✓ {file}")
        elif file:
            print(f"✗ {file} (缺失)")
    
    # 检查项目目录
    current_dir = Path.cwd()
    print(f"当前目录: {current_dir}")
    print("目录内容:")
    for item in sorted(current_dir.iterdir())[:10]:  # 只显示前10个
        print(f"  - {item.name}")
    if len(list(current_dir.iterdir())) > 10:
        print(f"  ... 还有{len(list(current_dir.iterdir()))-10}个文件/目录")
    print()

def check_wsgi_file():
    """检查WSGI配置"""
    print("=== WSGI配置检查 ===")
    wsgi_files = ['wsgi.py', 'app.py']
    
    for wsgi_file in wsgi_files:
        if os.path.exists(wsgi_file):
            print(f"找到WSGI文件: {wsgi_file}")
            try:
                with open(wsgi_file, 'r') as f:
                    content = f.read()
                    if 'application' in content or 'app' in content:
                        print(f"✓ {wsgi_file} 包含application对象")
                    else:
                        print(f"✗ {wsgi_file} 未找到application对象")
                    
                    # 检查常见问题
                    if 'if __name__ == "__main__":' in content:
                        print(f"⚠ {wsgi_file} 包含main检查，可能影响WSGI")
            except Exception as e:
                print(f"读取{wsgi_file}失败: {e}")
            break
    print()

def check_django_settings():
    """检查Django设置"""
    if os.path.exists('manage.py'):
        print("=== Django配置检查 ===")
        try:
            result = subprocess.run([sys.executable, 'manage.py', 'check'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print("✓ Django检查通过")
            else:
                print("✗ Django检查失败:")
                print(result.stdout)
                print(result.stderr)
        except subprocess.TimeoutExpired:
            print("✗ Django检查超时")
        except Exception as e:
            print(f"✗ Django检查出错: {e}")
        print()

def check_static_files():
    """检查静态文件配置"""
    print("=== 静态文件检查 ===")
    
    # 检查常见静态文件目录
    static_dirs = ['static', 'staticfiles', 'public']
    for dir_name in static_dirs:
        if os.path.exists(dir_name):
            print(f"✓ 找到静态目录: {dir_name}")
        
    # 检查settings.py中的静态文件配置
    settings_files = ['settings.py', 'myproject/settings.py', 'config/settings.py']
    for settings_file in settings_files:
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    content = f.read()
                    if 'STATIC_URL' in content:
                        print(f"✓ {settings_file} 包含STATIC_URL配置")
                    if 'STATIC_ROOT' in content:
                        print(f"✓ {settings_file} 包含STATIC_ROOT配置")
                    if 'MEDIA_URL' in content:
                        print(f"✓ {settings_file} 包含MEDIA_URL配置")
            except Exception:
                pass
            break
    print()

def check_database():
    """检查数据库配置"""
    print("=== 数据库检查 ===")
    if os.path.exists('manage.py'):
        try:
            result = subprocess.run([sys.executable, 'manage.py', 'migrate', '--dry-run'], 
                                  capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print("✓ 数据库迁移检查通过")
            else:
                print("⚠ 数据库可能需要迁移")
        except Exception as e:
            print(f"数据库检查出错: {e}")
    print()

def generate_report():
    """生成排查报告"""
    print("=== 生成完整报告 ===")
    report = {
        "python_version": sys.version,
        "working_directory": os.getcwd(),
        "files": os.listdir('.'),
        "timestamp": str(os.popen('date').read()).strip()
    }
    
    try:
        with open('deployment_debug_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print("✓ 报告已保存到 deployment_debug_report.json")
    except Exception as e:
        print(f"保存报告失败: {e}")
    print()

def main():
    print("PythonAnywhere部署问题排查脚本")
    print("=" * 50)
    
    check_python_version()
    check_dependencies()
    check_file_structure()
    check_wsgi_file()
    check_django_settings()
    check_static_files()
    check_database()
    generate_report()
    
    print("=" * 50)
    print("排查完成！")
    print("如果仍有问题，请提供:")
    print("1. 完整的错误信息")
    print("2. 项目的Web框架类型(Django/Flask等)")
    print("3. PythonAnywhere的配置详情")

if __name__ == "__main__":
    main()