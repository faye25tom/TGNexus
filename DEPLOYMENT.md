# Telegram Bot 聊天助手部署指南

## 🚀 快速部署

### 1. 环境准备

确保你的系统已安装：
- Docker
- Docker Compose
- Python 3.8+ (可选，用于运行启动脚本)

**注意**: 本项目使用预构建的 Docker 镜像 `fayetom/tgnexus:25.7`，无需本地构建。

### 2. 获取必要的 API 密钥

#### Telegram Bot Token
1. 在 Telegram 中搜索 `@BotFather`
2. 发送 `/newbot` 创建新机器人
3. 按提示设置机器人名称和用户名
4. 获取 Bot Token (格式类似: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### 获取聊天 ID
1. 将机器人添加到目标群组或私聊
2. 发送任意消息给机器人
3. 访问 `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. 在返回的 JSON 中找到 `chat.id` 字段

#### Gemini API Key
1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 创建新的 API Key
3. 复制生成的密钥

**注意**: 项目已更新为使用最新的 Gemini 2.5 Flash 模型，提供更快的响应速度和更好的性能。

### 3. 配置环境

```bash
# 克隆或下载项目
# 复制环境配置文件
cp .env.example .env

# 编辑 .env 文件，填入你的配置
nano .env
```

### 4. 启动服务

#### 方法一：使用启动脚本 (推荐)
```bash
python start.py
```

#### 方法二：直接使用 Docker Compose
```bash
# 创建必要目录
mkdir -p data logs

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 5. 访问配置后台

启动成功后，访问：http://localhost:32025

**首次登录信息：**
- 用户名：`admin`
- 密码：`admin123`

⚠️ **安全提醒**：首次登录后请立即修改默认密码！

**登录功能特性：**
- 🔐 安全的密码认证
- 🔒 账户锁定保护（5次失败后锁定15分钟）
- ⏰ 会话管理（默认1小时，可选择记住登录8小时）
- 🔑 在线修改密码
- 🚪 安全退出登录

在网页后台可以配置：
- Telegram Bot 设置
- Gemini AI 配置（支持 Gemini 2.5 Flash 模型）
- RSS 新闻源
- 定时任务
- 智能回复设置

**Gemini 2.5 Flash 特性：**
- ⚡ 更快的响应速度
- 🧠 更强的理解能力
- 💰 更优的成本效益
- 🔧 内置连接测试功能

## 📋 配置说明

### RSS 新闻源配置

在网页后台的 RSS 配置中，每行添加一个 RSS URL。推荐的新闻源：

```
https://feeds.bbci.co.uk/zhongwen/simp/rss.xml
https://rss.cnn.com/rss/edition.rss
https://techcrunch.com/feed/
https://www.theverge.com/rss/index.xml
```

### Prompt 配置

#### 新闻摘要 Prompt
```
请为以下新闻内容生成简洁的中文摘要，突出重点信息，按重要性排序：

{content}

要求：
1. 每条新闻用一句话概括
2. 突出关键信息和数据
3. 按重要性排序
4. 总字数控制在500字以内
```

#### 聊天回复 Prompt
```
你是一个友好、专业的聊天助手。请根据以下对话上下文，给出自然、有帮助的回复：

对话历史：
{context}

用户消息：{message}

回复要求：
1. 语气友好自然
2. 回答准确有用
3. 适当使用表情符号
4. 保持简洁明了
```

### 触发关键词

设置机器人回复的触发条件，例如：
- `@bot` - 直接提及机器人
- `机器人` - 包含"机器人"关键词
- `助手` - 包含"助手"关键词
- `?` 或 `？` - 问号表示提问

## 🔧 管理命令

### Docker 管理
```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新服务
docker-compose pull
docker-compose up -d
```

### 数据备份
```bash
# 备份数据库
cp data/bot.db data/bot.db.backup

# 备份配置
tar -czf backup.tar.gz data/ logs/
```

## 🐛 故障排除

### 常见问题

1. **Bot 无法启动**
   - 检查 Bot Token 是否正确
   - 确认网络连接正常
   - 查看日志：`docker-compose logs telegram-bot`

2. **无法生成新闻摘要**
   - 检查 Gemini API Key 是否有效
   - 确认 RSS 源可以访问
   - 检查定时任务配置

3. **机器人不回复消息**
   - 确认聊天 ID 配置正确
   - 检查触发关键词设置
   - 查看 Bot 是否有发送消息权限

4. **网页后台无法访问**
   - 确认端口 32025 未被占用
   - 检查防火墙设置
   - 查看容器是否正常运行

### 日志查看
```bash
# 查看实时日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs telegram-bot

# 查看最近的日志
docker-compose logs --tail=100
```

## 🔒 安全配置

### 管理后台认证

项目已内置登录认证功能，保护管理后台安全：

#### 默认登录信息
- **用户名**: `admin`
- **密码**: `admin123`

#### 自定义登录信息
在 `.env` 文件中配置：
```bash
# 管理后台认证配置
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_secure_password
JWT_SECRET_KEY=your-very-secure-jwt-secret-key
```

#### 安全建议

1. **立即修改默认密码**
   - 首次部署后立即修改默认登录信息
   - 使用强密码（至少8位，包含字母、数字、特殊字符）

2. **JWT 密钥安全**
   - 生成随机的 JWT 密钥：`openssl rand -hex 32`
   - 不要使用默认的密钥
   - 定期更换 JWT 密钥

3. **会话管理**
   - 默认会话时长：1小时（勾选"记住登录"为8小时）
   - 长时间不使用会自动退出
   - 支持手动退出登录

### 网络安全

1. **反向代理配置 (推荐)**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://localhost:32025;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

2. **HTTPS 配置**
   - 使用 Let's Encrypt 获取免费 SSL 证书
   - 强制 HTTPS 重定向
   - 启用 HSTS 头部

3. **防火墙设置**
   ```bash
   # 只允许特定 IP 访问
   sudo ufw allow from YOUR_IP_ADDRESS to any port 32025
   
   # 或者只允许本地访问
   sudo ufw allow from 127.0.0.1 to any port 32025
   ```

### API 密钥安全

1. **环境变量存储**
   - 所有敏感信息存储在 `.env` 文件中
   - 不要将 `.env` 文件提交到版本控制
   - 设置适当的文件权限：`chmod 600 .env`

2. **密钥轮换**
   - 定期更换 Telegram Bot Token
   - 定期更换 Gemini API Key
   - 监控 API 使用情况

### 数据安全

1. **数据库保护**
   - 数据库文件存储在 `data/` 目录
   - 定期备份数据库文件
   - 设置适当的目录权限

2. **日志安全**
   - 日志文件不包含敏感信息
   - 定期清理旧日志文件
   - 监控异常访问日志

### 生产环境部署建议

1. **使用专用服务器**
   - 不要在个人电脑上长期运行
   - 使用 VPS 或云服务器部署

2. **定期更新**
   - 及时更新 Docker 镜像
   - 关注安全公告和更新

3. **监控告警**
   - 设置服务状态监控
   - 配置异常情况告警

4. **备份策略**
   - 每日自动备份数据
   - 异地备份重要配置

## 📈 性能优化

1. **资源限制**
   ```yaml
   # 在 docker-compose.yml 中添加
   deploy:
     resources:
       limits:
         memory: 512M
         cpus: '0.5'
   ```

2. **日志轮转**
   ```yaml
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

## 🆕 更新升级

### 自动更新 (推荐)
```bash
# 使用启动脚本自动更新
python start.py
```

### 手动更新
```bash
# 1. 停止服务
docker-compose down

# 2. 备份数据
cp -r data data.backup

# 3. 拉取最新镜像
docker-compose pull

# 4. 启动服务
docker-compose up -d

# 5. 查看更新状态
docker-compose logs -f
```

### 版本回滚
如果新版本有问题，可以回滚到之前的版本：
```bash
# 停止服务
docker-compose down

# 修改 docker-compose.yml 中的镜像版本
# 例如：fayetom/tgnexus:25.6

# 启动服务
docker-compose up -d
```

## 📞 技术支持

如遇到问题，请：
1. 查看日志文件
2. 检查配置是否正确
3. 参考故障排除部分
4. 提交 Issue 并附上相关日志