import aiosqlite
import logging
import os

logger = logging.getLogger(__name__)

async def init_db():
    """初始化数据库"""
    # 确保数据目录存在
    os.makedirs("data", exist_ok=True)
    
    try:
        async with aiosqlite.connect("data/bot.db") as db:
            # 创建配置表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    section TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建聊天历史表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT NOT NULL,
                    user_id TEXT,
                    username TEXT,
                    message TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建新闻摘要历史表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS news_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.commit()
            logger.info("数据库初始化完成")
            
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

async def save_chat_message(chat_id: str, user_id: str, username: str, message: str):
    """保存聊天消息"""
    try:
        async with aiosqlite.connect("data/bot.db") as db:
            await db.execute(
                "INSERT INTO chat_history (chat_id, user_id, username, message) VALUES (?, ?, ?, ?)",
                (chat_id, user_id, username, message)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"保存聊天消息失败: {e}")

async def get_recent_chat_history(chat_id: str, limit: int = 10) -> list:
    """获取最近的聊天历史"""
    try:
        async with aiosqlite.connect("data/bot.db") as db:
            cursor = await db.execute(
                "SELECT username, message, timestamp FROM chat_history WHERE chat_id = ? ORDER BY timestamp DESC LIMIT ?",
                (chat_id, limit)
            )
            rows = await cursor.fetchall()
            return [(row[0], row[1], row[2]) for row in reversed(rows)]
    except Exception as e:
        logger.error(f"获取聊天历史失败: {e}")
        return []

async def save_news_summary(title: str, summary: str, source_url: str = None):
    """保存新闻摘要"""
    try:
        async with aiosqlite.connect("data/bot.db") as db:
            await db.execute(
                "INSERT INTO news_summary (title, summary, source_url) VALUES (?, ?, ?)",
                (title, summary, source_url)
            )
            await db.commit()
    except Exception as e:
        logger.error(f"保存新闻摘要失败: {e}")