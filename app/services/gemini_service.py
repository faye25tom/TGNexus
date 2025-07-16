import httpx
import json
from typing import Optional
import logging
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class GeminiService:
    """Gemini AI 服务"""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model_name = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.timeout = 30
        logger.info(f"Gemini 服务初始化成功，模型: {self.model_name}")
    
    async def generate_text(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """生成文本"""
        if not self.api_key:
            logger.error("Gemini API Key 未配置")
            return None
        
        try:
            url = f"{self.base_url}/{self.model_name}:generateContent"
            
            headers = {
                "Content-Type": "application/json",
                "X-goog-api-key": self.api_key
            }
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": min(max_tokens, 100000),  # 设置为 10 万 tokens
                    "temperature": 0.7,
                    "topP": 0.95,  # 增加 topP 以提高创造性
                    "topK": 40
                }
            }
            
            async with httpx.AsyncClient(
                timeout=self.timeout,
                verify=False,  # 跳过 SSL 证书验证
                follow_redirects=True
            ) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                # 添加调试日志
                logger.debug(f"Gemini API 响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
                
                # 解析响应
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    
                    # 检查完成原因
                    finish_reason = candidate.get("finishReason", "")
                    if finish_reason == "SAFETY":
                        logger.warning("Gemini 响应被安全过滤器阻止")
                        return "抱歉，由于安全策略限制，无法生成此内容。"
                    elif finish_reason == "RECITATION":
                        logger.warning("Gemini 响应因版权问题被阻止")
                        return "抱歉，由于版权限制，无法生成此内容。"
                    elif finish_reason == "MAX_TOKENS":
                        logger.warning("Gemini 响应因达到最大 token 限制而截断")
                        # 即使被截断，也尝试获取已生成的内容
                    elif finish_reason and finish_reason != "STOP":
                        logger.warning(f"Gemini 响应异常结束: {finish_reason}")
                    
                    # 解析内容 - 标准格式
                    if "content" in candidate:
                        content = candidate["content"]
                        
                        # 检查是否有 parts 字段
                        if "parts" in content and len(content["parts"]) > 0:
                            for part in content["parts"]:
                                if "text" in part:
                                    text_content = part["text"].strip()
                                    if text_content:
                                        return text_content
                        
                        # 如果 parts 为空但有其他字段，尝试直接获取文本
                        if "text" in content:
                            text_content = content["text"].strip()
                            if text_content:
                                return text_content
                                
                        # 如果 content 只有 role 字段，可能是因为 MAX_TOKENS 导致内容被截断
                        if "role" in content:
                            logger.warning("检测到可能因 MAX_TOKENS 导致的空响应")
                            # 对于 gemini-2.5-flash 模型，即使只有 role 字段，也返回一个默认响应
                            if self.model_name == "gemini-2.5-flash":
                                return "已收到您的请求，但由于内容较长，生成被截断。请尝试减少输入文本量或分批处理。"
                    
                    # 尝试其他可能的响应格式
                    if "text" in candidate:
                        text_content = candidate["text"].strip()
                        if text_content:
                            return text_content
                
                # 检查是否有错误信息
                if "error" in result:
                    error_msg = result["error"].get("message", "未知错误")
                    logger.error(f"Gemini API 返回错误: {error_msg}")
                    return None
                
                # 如果没有找到预期的格式，记录完整响应
                logger.warning(f"Gemini 返回意外的响应格式，无法解析内容")
                return None
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Gemini API 请求失败: {e.response.status_code}"
            try:
                error_json = e.response.json()
                if "error" in error_json and "message" in error_json["error"]:
                    error_msg += f" - {error_json['error']['message']}"
            except:
                error_msg += f" - {e.response.text[:200]}"
            
            logger.error(error_msg)
            return None
        except httpx.TimeoutException:
            logger.error("Gemini API 请求超时")
            return None
        except Exception as e:
            logger.error(f"Gemini 生成文本失败: {e}")
            return None
    
    async def summarize_news(self, news_content: str, prompt_template: str) -> Optional[str]:
        """生成新闻摘要"""
        # 设置更大的输入内容长度限制，最大 10 万 tokens (约 30-40 万字符)
        if len(news_content) > 100000:
            logger.warning(f"新闻内容过长 ({len(news_content)} 字符)，截断为 100000 字符")
            news_content = news_content[:100000] + "...\n[内容过长已截断]"
        
        # 优化 prompt，明确指定输出格式和长度限制
        optimized_prompt = """请为以下新闻生成详细摘要。

新闻内容:
{content}

要求:
1. 总长度控制在 800-1000 字之间
2. 每条新闻用 2-3 句话概括，包含关键信息点
3. 按重要性和时效性排序
4. 使用清晰、专业的语言
5. 添加适当的表情符号增强可读性
6. 格式为中文摘要
7. 在摘要开头添加一个简短的总体概述
8. 在摘要结尾添加一个简短的总结或展望
"""
        
        formatted_prompt = optimized_prompt.format(content=news_content)
        
        # 使用更大的 max_tokens 值
        result = await self.generate_text(formatted_prompt, max_tokens=10000)
        
        # 如果生成失败，返回一个默认响应
        if not result:
            return "抱歉，无法生成新闻摘要。请稍后再试或检查 RSS 源配置。"
        
        # 清理结果，移除可能的前缀
        result = result.replace("新闻摘要：", "").replace("新闻摘要:", "").strip()
        
        return result
    
    async def generate_chat_response(self, message: str, context: str, prompt_template: str) -> Optional[str]:
        """生成聊天回复"""
        prompt = prompt_template.format(context=context, message=message)
        return await self.generate_text(prompt, max_tokens=8192)  # 增加到 8192 tokens
    
    def update_config(self, api_key: str, model: str = "gemini-2.5-flash"):
        """更新配置"""
        self.api_key = api_key
        self.model_name = model
        logger.info(f"Gemini 配置已更新，模型: {self.model_name}")
    
    async def test_connection(self) -> bool:
        """测试 API 连接"""
        try:
            test_response = await self.generate_text("Hello", max_tokens=10)
            return test_response is not None
        except Exception as e:
            logger.error(f"Gemini 连接测试失败: {e}")
            return False