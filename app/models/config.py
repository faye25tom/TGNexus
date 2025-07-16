import json
import aiosqlite
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, db_path: str = "data/bot.db"):
        self.db_path = db_path
        self.default_config = {
            "telegram": {
                "bot_token": "",
                "chat_id": ""
            },
            "gemini": {
                "api_key": "",
                "model": "gemini-2.5-flash"
            },
            "rss": {
                "feeds": [],
                "summary_time": "09:00"
            },
            "prompts": {
                "news_summary": "请为以下新闻内容生成简洁的中文摘要，突出重点信息：\n\n{content}",
                "chat_response": "你是一个友好的聊天助手，请根据以下对话上下文，给出自然、有帮助的回复：\n\n{context}\n\n用户消息：{message}",
                "trigger_keywords": ["@bot", "机器人", "助手", "?", "？"]
            }
        }
    
    async def get_config(self, section: str) -> Dict[str, Any]:
        """获取指定配置段"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT value FROM config WHERE section = ?", (section,)
                )
                row = await cursor.fetchone()
                
                if row:
                    return json.loads(row[0])
                else:
                    # 返回默认配置
                    default = self.default_config.get(section, {})
                    await self.update_config(section, default)
                    return default
        except Exception as e:
            logger.error(f"获取配置失败 {section}: {e}")
            return self.default_config.get(section, {})
    
    async def update_config(self, section: str, config: Dict[str, Any]):
        """更新配置"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT OR REPLACE INTO config (section, value) VALUES (?, ?)",
                    (section, json.dumps(config, ensure_ascii=False))
                )
                await db.commit()
                logger.info(f"配置已更新: {section}")
        except Exception as e:
            logger.error(f"更新配置失败 {section}: {e}")
            raise
    
    async def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        all_config = {}
        for section in self.default_config.keys():
            all_config[section] = await self.get_config(section)
        return all_config
    
    async def get_telegram_config(self) -> Dict[str, str]:
        """获取 Telegram 配置"""
        return await self.get_config("telegram")
    
    async def get_gemini_config(self) -> Dict[str, str]:
        """获取 Gemini 配置"""
        return await self.get_config("gemini")
    
    async def get_rss_config(self) -> Dict[str, Any]:
        """获取 RSS 配置"""
        return await self.get_config("rss")
    
    async def get_prompts_config(self) -> Dict[str, Any]:
        """获取 Prompts 配置"""
        return await self.get_config("prompts")