#!/usr/bin/env python3
"""
Telegram Bot 聊天助手启动脚本
"""

import os
import sys
import subprocess
import platform

def check_docker():
    """检查 Docker 是否安装"""
    try:
        subprocess.run(['docker', '--version'], check=True, capture_output=True)
        subprocess.run(['docker-compose', '--version'], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def create_directories():
    """创建必要的目录"""
    directories = ['data', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ 创建目录: {directory}")

def check_env_file():
    """检查环境配置文件"""
    if not os.path.exists('.env'):
        print("⚠️  未找到 .env 文件")
        print("请复制 .env.example 为 .env 并配置相关参数")
        return False
    return True

def main():
    print("🤖 Telegram Bot 聊天助手启动器")
    print("=" * 40)
    
    # 检查 Docker
    if not check_docker():
        print("❌ Docker 或 Docker Compose 未安装")
        print("请先安装 Docker 和 Docker Compose")
        sys.exit(1)
    
    print("✓ Docker 环境检查通过")
    
    # 创建目录
    create_directories()
    
    # 检查环境文件
    if not check_env_file():
        print("\n📝 配置步骤:")
        print("1. 复制 .env.example 为 .env")
        print("2. 编辑 .env 文件，填入你的配置")
        print("3. 重新运行此脚本")
        return
    
    print("✓ 环境配置检查通过")
    
    # 拉取最新镜像
    print("\n📥 拉取最新镜像...")
    try:
        subprocess.run(['docker', 'pull', 'fayetom/tgnexus:25.7'], check=True)
        print("✓ 镜像拉取完成")
    except subprocess.CalledProcessError:
        print("⚠️  镜像拉取失败，将使用本地镜像")
    
    # 启动服务
    print("\n🚀 启动 Telegram Bot 服务...")
    try:
        subprocess.run(['docker-compose', 'up', '-d'], check=True)
        
        print("✅ 服务启动成功!")
        print("\n📊 访问配置后台: http://localhost:32025")
        print("🔧 查看日志: docker-compose logs -f")
        print("⏹️  停止服务: docker-compose down")
        print("🔄 更新服务: docker-compose pull && docker-compose up -d")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()