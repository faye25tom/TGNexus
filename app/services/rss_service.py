import feedparser
import httpx
from typing import List, Dict, Any
import logging
from datetime import datetime, timedelta
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class RSSService:
    """RSS 新闻服务"""
    
    def __init__(self):
        self.timeout = 30
    
    async def fetch_feed(self, url: str) -> List[Dict[str, Any]]:
        """获取单个 RSS 源的新闻"""
        try:
            # 配置 HTTP 客户端，跳过 SSL 验证以避免证书问题
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=False,  # 跳过 SSL 证书验证
                follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                feed = feedparser.parse(response.text)
                
                if feed.bozo:
                    logger.warning(f"RSS 源可能有问题: {url}")
                
                articles = []
                for entry in feed.entries[:10]:  # 限制每个源最多10篇文章
                    article = {
                        'title': entry.get('title', '无标题'),
                        'link': entry.get('link', ''),
                        'summary': entry.get('summary', entry.get('description', '')),
                        'published': entry.get('published', ''),
                        'source': feed.feed.get('title', url)
                    }
                    articles.append(article)
                
                logger.info(f"从 {url} 获取到 {len(articles)} 篇文章")
                return articles
                
        except Exception as e:
            logger.error(f"获取 RSS 源失败 {url}: {e}")
            return []
    
    async def fetch_multiple_feeds(self, urls: List[str]) -> List[Dict[str, Any]]:
        """获取多个 RSS 源的新闻"""
        all_articles = []
        
        for url in urls:
            articles = await self.fetch_feed(url)
            all_articles.extend(articles)
        
        # 按发布时间排序（最新的在前）
        all_articles.sort(key=lambda x: self._parse_date(x.get('published', '')), reverse=True)
        
        logger.info(f"总共获取到 {len(all_articles)} 篇文章")
        return all_articles
    
    def _parse_date(self, date_str: str) -> datetime:
        """解析日期字符串"""
        if not date_str:
            return datetime.min.replace(tzinfo=None)
        
        try:
            # 尝试解析常见的日期格式
            from email.utils import parsedate_to_datetime
            parsed_date = parsedate_to_datetime(date_str)
            # 转换为 naive datetime（移除时区信息）
            if parsed_date.tzinfo is not None:
                parsed_date = parsed_date.replace(tzinfo=None)
            return parsed_date
        except:
            try:
                # 尝试 ISO 格式
                parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                # 转换为 naive datetime（移除时区信息）
                if parsed_date.tzinfo is not None:
                    parsed_date = parsed_date.replace(tzinfo=None)
                return parsed_date
            except:
                return datetime.min.replace(tzinfo=None)
    
    def filter_recent_articles(self, articles: List[Dict[str, Any]], hours: int = 24) -> List[Dict[str, Any]]:
        """过滤最近的文章"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_articles = []
        
        for article in articles:
            pub_date = self._parse_date(article.get('published', ''))
            if pub_date > cutoff_time:
                recent_articles.append(article)
        
        return recent_articles
    
    def format_articles_for_summary(self, articles: List[Dict[str, Any]]) -> str:
        """格式化文章用于摘要生成"""
        formatted_content = []
        
        # 进一步减少处理的文章数量，从10篇减少到8篇
        for i, article in enumerate(articles[:8], 1):
            # 简化格式，减少不必要的文本
            content = f"{i}. {article['title']} ({article['source']})\n"
            
            # 只有当摘要不为空且不是HTML时才添加摘要
            if article.get('summary') and not (article['summary'].startswith('<') and '>' in article['summary']):
                # 进一步限制摘要长度，从100字符减少到80字符
                summary = article['summary'][:80] + "..." if len(article['summary']) > 80 else article['summary']
                # 清理摘要中的HTML标签
                summary = summary.replace('<p>', '').replace('</p>', '').replace('<br>', '')
                content += f"   {summary}\n"
            
            formatted_content.append(content)
        
        # 添加指导说明
        formatted_content.insert(0, "以下是最近的新闻文章，请生成简短摘要：\n")
        
        return "\n".join(formatted_content)