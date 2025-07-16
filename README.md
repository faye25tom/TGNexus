# Telegram Bot 聊天助手

一个智能的 Telegram Bot，具备定时新闻摘要和智能互动功能。

## 功能特性

- 🗞️ **定时新闻摘要**: 每天定时从 RSS 源获取并生成新闻摘要
- 🤖 **智能互动**: 基于 Gemini LLM 的智能对话和问题解答
- 🌐 **网页配置后台**: 可视化配置界面，管理所有设置
- 🐳 **Docker 部署**: 一键部署，简单易用

## 技术栈

- **后端**: Python + FastAPI
- **前端**: HTML + JavaScript + Bootstrap
- **数据库**: SQLite
- **LLM**: Google Gemini API
- **部署**: Docker + Docker Compose

## 快速开始

1. 克隆项目并进入目录
2. 配置环境变量
3. 使用 Docker Compose 启动：
   ```bash
   docker-compose up -d
   ```
4. 访问配置后台：http://localhost:32025

## 配置说明

通过网页后台可以配置：
- Telegram Bot Token
- Gemini API Key
- RSS 订阅源
- 定时任务设置
- 智能回复触发条件
- 自定义 Prompt

## 项目结构

```
telegram-bot-assistant/
├── app/                    # 应用主目录
│   ├── main.py            # FastAPI 主应用
│   ├── bot/               # Telegram Bot 相关
│   ├── services/          # 服务层
│   ├── models/            # 数据模型
│   └── static/            # 静态文件
├── docker-compose.yml     # Docker 编排文件
├── Dockerfile            # Docker 镜像构建
└── requirements.txt      # Python 依赖
```