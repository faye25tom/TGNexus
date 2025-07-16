from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from datetime import datetime

from .rss_service import RSSService
from .gemini_service import GeminiService
from .database import save_news_summary
from ..models.config import ConfigManager

logger = logging.getLogger(__name__)

class SchedulerService:
    """调度服务"""
    
    def __init__(self, bot_service, config_manager: ConfigManager):
        self.bot_service = bot_service
        self.config_manager = config_manager
        self.scheduler = AsyncIOScheduler()
        self.rss_service = RSSService()
        self.is_running = False
    
    def start(self):
        """启动调度器"""
        try:
            self.scheduler.start()
            self.is_running = True
            
            # 调度新闻摘要任务
            asyncio.create_task(self.schedule_news_summary())
            
            logger.info("调度服务启动成功")
        except Exception as e:
            logger.error(f"启动调度服务失败: {e}")
    
    def stop(self):
        """停止调度器"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("调度服务已停止")
    
    async def schedule_news_summary(self):
        """调度新闻摘要任务"""
        try:
            rss_config = await self.config_manager.get_rss_config()
            summary_time = rss_config.get('summary_time', '09:00')
            
            # 解析时间
            hour, minute = map(int, summary_time.split(':'))
            
            # 移除现有的新闻摘要任务
            self.scheduler.remove_all_jobs()
            
            # 添加新的定时任务
            self.scheduler.add_job(
                self.generate_news_summary,
                CronTrigger(hour=hour, minute=minute),
                id='news_summary',
                name='每日新闻摘要',
                replace_existing=True
            )
            
            logger.info(f"新闻摘要任务已调度，时间: {summary_time}")
            
        except Exception as e:
            logger.error(f"调度新闻摘要任务失败: {e}")
    
    def reschedule_news_summary(self):
        """重新调度新闻摘要"""
        import asyncio
        asyncio.create_task(self.schedule_news_summary())
    
    async def generate_news_summary(self):
        """生成新闻摘要"""
        try:
            logger.info("开始生成新闻摘要")
            
            # 获取配置
            rss_config = await self.config_manager.get_rss_config()
            gemini_config = await self.config_manager.get_gemini_config()
            prompts_config = await self.config_manager.get_prompts_config()
            
            feeds = rss_config.get('feeds', [])
            if not feeds:
                logger.warning("未配置 RSS 源")
                return
            
            if not gemini_config.get('api_key'):
                logger.warning("未配置 Gemini API Key")
                return
            
            # 获取新闻
            articles = await self.rss_service.fetch_multiple_feeds(feeds)
            if not articles:
                logger.warning("未获取到新闻文章")
                return
            
            # 过滤最近48小时的文章（扩大时间范围）
            recent_articles = self.rss_service.filter_recent_articles(articles, 48)
            if not recent_articles or len(recent_articles) < 3:
                # 如果没有足够的最近文章，使用最新的8篇
                recent_articles = articles[:8]
            
            # 格式化文章内容
            formatted_content = self.rss_service.format_articles_for_summary(recent_articles)
            
            # 生成摘要
            gemini_service = GeminiService(
                gemini_config['api_key'],
                gemini_config.get('model', 'gemini-2.5-flash')
            )
            
            prompt_template = prompts_config.get('news_summary',
                "请为以下新闻内容生成简洁的中文摘要，突出重点信息：\n\n{content}")
            
            summary = await gemini_service.summarize_news(formatted_content, prompt_template)
            
            if summary:
                # 保存摘要到数据库
                await save_news_summary(
                    f"每日新闻摘要 - {datetime.now().strftime('%Y-%m-%d')}",
                    summary
                )
                
                # 发送到 Telegram
                await self.bot_service.send_news_summary(summary)
                
                logger.info("新闻摘要生成并发送成功")
            else:
                logger.error("生成新闻摘要失败")
                
        except Exception as e:
            logger.error(f"生成新闻摘要时出错: {e}")

import asyncio