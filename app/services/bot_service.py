from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging
from typing import Optional
from datetime import datetime

from .gemini_service import GeminiService
from .database import save_chat_message, get_recent_chat_history
from ..models.config import ConfigManager

logger = logging.getLogger(__name__)

class BotService:
    """Telegram Bot 服务"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.application: Optional[Application] = None
        self.gemini_service: Optional[GeminiService] = None
        self.is_running = False
        self.target_chat_id = None
    
    async def start(self):
        """启动 Bot"""
        try:
            # 获取配置
            telegram_config = await self.config_manager.get_telegram_config()
            gemini_config = await self.config_manager.get_gemini_config()
            
            if not telegram_config.get('bot_token'):
                logger.warning("Telegram Bot Token 未配置")
                return
            
            if not gemini_config.get('api_key'):
                logger.warning("Gemini API Key 未配置")
                return
            
            # 初始化 Gemini 服务
            self.gemini_service = GeminiService(
                gemini_config['api_key'],
                gemini_config.get('model', 'gemini-pro')
            )
            
            # 设置目标聊天 ID
            self.target_chat_id = telegram_config.get('chat_id')
            
            # 创建 Bot 应用
            self.application = Application.builder().token(telegram_config['bot_token']).build()
            
            # 添加处理器
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # 启动 Bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.is_running = True
            logger.info("Telegram Bot 启动成功")
            
        except Exception as e:
            logger.error(f"启动 Telegram Bot 失败: {e}")
            self.is_running = False
            raise
    
    async def stop(self):
        """停止 Bot"""
        if self.application and self.is_running:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                self.is_running = False
                logger.info("Telegram Bot 已停止")
            except Exception as e:
                logger.error(f"停止 Telegram Bot 失败: {e}")
    
    async def restart(self):
        """重启 Bot"""
        await self.stop()
        await self.start()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        welcome_message = """
🤖 欢迎使用智能聊天助手！

我可以为您提供以下服务：
📰 定时新闻摘要
💬 智能对话互动
❓ 问题解答

使用 /help 查看更多命令
        """
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令"""
        help_message = """
🔧 可用命令：

/start - 开始使用
/help - 显示帮助信息
/status - 查看 Bot 状态

💡 使用技巧：
• 直接发送消息与我对话
• 提问时我会智能回复
• 每天定时为您推送新闻摘要
        """
        await update.message.reply_text(help_message)
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /status 命令"""
        status_message = f"""
📊 Bot 状态：

🟢 运行状态: {"正常" if self.is_running else "异常"}
🤖 AI 服务: {"已连接" if self.gemini_service else "未连接"}
💬 聊天 ID: {update.effective_chat.id}
        """
        await update.message.reply_text(status_message)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理普通消息"""
        try:
            user = update.effective_user
            chat = update.effective_chat
            message_text = update.message.text
            
            # 保存聊天记录
            await save_chat_message(
                str(chat.id),
                str(user.id),
                user.username or user.first_name,
                message_text
            )
            
            # 检查是否需要回复
            if await self.should_respond(message_text, chat.id):
                response = await self.generate_response(message_text, str(chat.id))
                if response:
                    await update.message.reply_text(response)
            
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
    
    async def should_respond(self, message: str, chat_id: int) -> bool:
        """判断是否应该回复消息"""
        try:
            prompts_config = await self.config_manager.get_prompts_config()
            trigger_keywords = prompts_config.get('trigger_keywords', [])
            
            # 检查触发关键词
            message_lower = message.lower()
            for keyword in trigger_keywords:
                if keyword.lower() in message_lower:
                    return True
            
            # 如果是私聊，总是回复
            if str(chat_id) == self.target_chat_id:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"判断是否回复失败: {e}")
            return False
    
    async def generate_response(self, message: str, chat_id: str) -> Optional[str]:
        """生成回复"""
        if not self.gemini_service:
            return "抱歉，AI 服务暂时不可用。"
        
        try:
            # 获取聊天历史
            chat_history = await get_recent_chat_history(chat_id, 5)
            context = "\n".join([f"{username}: {msg}" for username, msg, _ in chat_history])
            
            # 获取回复 prompt
            prompts_config = await self.config_manager.get_prompts_config()
            prompt_template = prompts_config.get('chat_response', 
                "请根据以下对话上下文，给出自然、有帮助的回复：\n\n{context}\n\n用户消息：{message}")
            
            # 生成回复
            response = await self.gemini_service.generate_chat_response(
                message, context, prompt_template
            )
            
            return response or "抱歉，我现在无法理解您的消息。"
            
        except Exception as e:
            logger.error(f"生成回复失败: {e}")
            return "抱歉，处理您的消息时出现了错误。"
    
    async def send_message(self, message: str):
        """发送消息到指定聊天"""
        if not self.application or not self.target_chat_id:
            logger.warning("Bot 未配置或未启动")
            return
        
        try:
            await self.application.bot.send_message(
                chat_id=self.target_chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info("消息发送成功")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
    
    async def send_news_summary(self, summary: str):
        """发送新闻摘要"""
        header = "📰 *今日新闻摘要*\n\n"
        footer = f"\n\n_更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}_"
        
        # 限制消息长度，Telegram 单条消息最大 4096 字符
        max_content_length = 4096 - len(header) - len(footer)
        if len(summary) > max_content_length:
            summary = summary[:max_content_length-3] + "..."
        
        full_message = header + summary + footer
        await self.send_message(full_message)