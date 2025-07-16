from fastapi import FastAPI, Request, Form, HTTPException, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBearer
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import timedelta

from .services.database import init_db
from .services.bot_service import BotService
from .services.scheduler_service import SchedulerService
from .services.auth_service import auth_service
from .models.config import ConfigManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局服务实例
bot_service = None
scheduler_service = None
config_manager = ConfigManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global bot_service, scheduler_service
    
    # 启动时初始化
    await init_db()
    bot_service = BotService(config_manager)
    scheduler_service = SchedulerService(bot_service, config_manager)
    
    # 启动服务
    await bot_service.start()
    scheduler_service.start()
    
    logger.info("Telegram Bot Assistant 启动成功")
    
    yield
    
    # 关闭时清理
    if bot_service:
        await bot_service.stop()
    if scheduler_service:
        scheduler_service.stop()
    
    logger.info("Telegram Bot Assistant 已停止")

app = FastAPI(
    title="Telegram Bot Assistant",
    description="智能 Telegram Bot 聊天助手",
    version="1.0.0",
    lifespan=lifespan
)

# 静态文件和模板
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# 认证依赖函数
def require_auth(request: Request):
    """需要认证的依赖函数"""
    if not auth_service.check_session(request):
        # 对于 API 请求，返回 401 错误
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="需要登录"
        )

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "message": "Telegram Bot Assistant is running"}

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    """登录页面"""
    # 如果已经登录，重定向到主页
    if auth_service.check_session(request):
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error
    })

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember: bool = Form(False)
):
    """处理登录"""
    try:
        user = auth_service.authenticate_user(username, password)
        if not user:
            # 获取失败次数信息
            admin_user = auth_service.admin_users.get(username)
            failed_attempts = admin_user.get("failed_attempts", 0) if admin_user else 0
            remaining_attempts = auth_service.max_failed_attempts - failed_attempts
            
            error_msg = "用户名或密码错误"
            if failed_attempts > 0:
                error_msg += f"，还有 {remaining_attempts} 次尝试机会"
            
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": error_msg,
                "username": username
            })
        
        # 创建访问令牌
        access_token_expires = timedelta(minutes=480 if remember else 60)  # 记住登录8小时，否则1小时
        access_token = auth_service.create_access_token(
            data={"sub": user["username"]}, 
            expires_delta=access_token_expires
        )
        
        # 重定向到主页并设置cookie
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=int(access_token_expires.total_seconds()) if remember else None,
            httponly=True,
            secure=False,  # 在生产环境中应该设置为True
            samesite="lax"
        )
        
        logger.info(f"用户 {username} 登录成功")
        return response
        
    except HTTPException as e:
        # 处理账户锁定异常
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": e.detail,
            "username": username
        })

@app.post("/logout")
async def logout():
    """登出"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="access_token")
    return response

@app.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    _: None = Depends(require_auth)
):
    """修改密码"""
    try:
        # 获取当前用户名
        token = request.cookies.get("access_token")
        token_data = auth_service.verify_token(token)
        current_username = token_data["username"] if token_data else "admin"
        
        # 验证当前密码
        try:
            user = auth_service.authenticate_user(current_username, current_password)
            if not user:
                return {"status": "error", "message": "当前密码错误"}
        except HTTPException:
            return {"status": "error", "message": "当前密码错误"}
        
        # 验证新密码长度
        if len(new_password) < 6:
            return {"status": "error", "message": "新密码长度至少6位"}
        
        # 检查新密码是否与当前密码相同
        if auth_service.verify_password(new_password, user["hashed_password"]):
            return {"status": "error", "message": "新密码不能与当前密码相同"}
        
        # 更新密码
        if auth_service.update_password(current_username, new_password):
            logger.info(f"用户 {current_username} 密码修改成功")
            return {"status": "success", "message": "密码修改成功，请重新登录"}
        else:
            return {"status": "error", "message": "密码更新失败"}
        
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return {"status": "error", "message": "修改密码失败"}

@app.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request, _: None = Depends(require_auth)):
    """修改密码页面"""
    return templates.TemplateResponse("change_password.html", {
        "request": request
    })

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """主页面 - 配置仪表板"""
    # 检查登录状态，未登录则重定向到登录页面
    if not auth_service.check_session(request):
        return RedirectResponse(url="/login", status_code=303)
    
    config = await config_manager.get_all_config()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "config": config,
        "bot_status": "运行中" if bot_service and bot_service.is_running else "已停止"
    })

@app.post("/config/telegram")
async def update_telegram_config(
    request: Request,
    bot_token: str = Form(...),
    chat_id: str = Form(...),
    _: None = Depends(require_auth)
):
    """更新 Telegram 配置"""
    try:
        await config_manager.update_config("telegram", {
            "bot_token": bot_token,
            "chat_id": chat_id
        })
        
        # 重启 Bot 服务
        if bot_service:
            await bot_service.restart()
        
        return RedirectResponse(url="/?success=telegram_updated", status_code=303)
    except Exception as e:
        logger.error(f"更新 Telegram 配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/gemini")
async def update_gemini_config(
    request: Request,
    api_key: str = Form(...),
    model: str = Form("gemini-2.5-flash"),
    _: None = Depends(require_auth)
):
    """更新 Gemini 配置"""
    try:
        await config_manager.update_config("gemini", {
            "api_key": api_key,
            "model": model
        })
        return RedirectResponse(url="/?success=gemini_updated", status_code=303)
    except Exception as e:
        logger.error(f"更新 Gemini 配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/rss")
async def update_rss_config(
    request: Request,
    feeds: str = Form(...),
    summary_time: str = Form("09:00"),
    _: None = Depends(require_auth)
):
    """更新 RSS 配置"""
    try:
        feed_list = [feed.strip() for feed in feeds.split('\n') if feed.strip()]
        await config_manager.update_config("rss", {
            "feeds": feed_list,
            "summary_time": summary_time
        })
        
        # 重新调度任务
        if scheduler_service:
            scheduler_service.reschedule_news_summary()
        
        return RedirectResponse(url="/?success=rss_updated", status_code=303)
    except Exception as e:
        logger.error(f"更新 RSS 配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/prompts")
async def update_prompts_config(
    request: Request,
    news_summary_prompt: str = Form(...),
    chat_response_prompt: str = Form(...),
    trigger_keywords: str = Form(...),
    _: None = Depends(require_auth)
):
    """更新 Prompt 配置"""
    try:
        keywords = [kw.strip() for kw in trigger_keywords.split(',') if kw.strip()]
        await config_manager.update_config("prompts", {
            "news_summary": news_summary_prompt,
            "chat_response": chat_response_prompt,
            "trigger_keywords": keywords
        })
        return RedirectResponse(url="/?success=prompts_updated", status_code=303)
    except Exception as e:
        logger.error(f"更新 Prompt 配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bot/restart")
async def restart_bot(request: Request, _: None = Depends(require_auth)):
    """重启 Bot"""
    try:
        if bot_service:
            await bot_service.restart()
        return {"status": "success", "message": "Bot 重启成功"}
    except Exception as e:
        logger.error(f"重启 Bot 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/news/manual-summary")
async def manual_news_summary(request: Request, _: None = Depends(require_auth)):
    """手动触发新闻摘要"""
    try:
        if scheduler_service:
            await scheduler_service.generate_news_summary()
        return {"status": "success", "message": "新闻摘要生成完成"}
    except Exception as e:
        logger.error(f"生成新闻摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gemini/test")
async def test_gemini_connection(request: Request, _: None = Depends(require_auth)):
    """测试 Gemini API 连接"""
    try:
        from .services.gemini_service import GeminiService
        
        # 获取当前 Gemini 配置
        gemini_config = await config_manager.get_gemini_config()
        
        if not gemini_config.get('api_key'):
            return {"status": "error", "message": "请先配置 Gemini API Key"}
        
        # 创建 Gemini 服务实例并测试连接
        gemini_service = GeminiService(
            gemini_config['api_key'],
            gemini_config.get('model', 'gemini-2.5-flash')
        )
        
        # 测试简单的文本生成
        test_result = await gemini_service.generate_text("请回复'连接成功'", max_tokens=50)
        
        if test_result:
            return {
                "status": "success", 
                "message": f"Gemini API 连接成功！模型: {gemini_config.get('model', 'gemini-2.5-flash')}",
                "response": test_result[:100] + "..." if len(test_result) > 100 else test_result
            }
        else:
            return {"status": "error", "message": "Gemini API 连接失败，请检查 API Key 和网络连接"}
            
    except Exception as e:
        logger.error(f"测试 Gemini 连接失败: {e}")
        return {"status": "error", "message": f"连接测试失败: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=32025)