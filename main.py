"""
主应用入口文件 - FastAPI应用启动和配置

此文件负责：
- 初始化FastAPI应用
- 配置日志记录
- 设置应用生命周期管理
- 注册路由和中间件
- 启动定时任务调度器
- 配置静态文件服务

Author: music-monitor development team
"""


from core.config import config as global_config, load_config
global_config.update(load_config())
import logging
import yaml
import os
import sys


from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from datetime import datetime
import collections
from urllib.parse import quote

from core.database import init_db, SessionLocal
from app.models.media_record import MediaRecord
from app.services.notification import NotificationService
from core.scheduler import scheduler  # 全局调度器单例 (供设置页重排共享)

# 创建调度器实例
# scheduler = AsyncIOScheduler()

from fastapi import Request, Response, Query
from wechatpy.crypto import WeChatCrypto, PrpCrypto
from wechatpy import parse_message, create_reply
from wechatpy.exceptions import InvalidSignatureException
import xmltodict
from starlette.middleware.sessions import SessionMiddleware
from typing import Optional
from pydantic import BaseModel


def setup_logging():
    # Configure logging
    LOG_DIR = "/config/logs" if os.path.exists("/config") else "logs"
    os.makedirs(LOG_DIR, exist_ok=True)
    LOG_FILE = os.path.join(LOG_DIR, "application.log")

    from logging.handlers import TimedRotatingFileHandler

    # Basic Config (Console)
    file_handler = TimedRotatingFileHandler(
        LOG_FILE, 
        when='midnight', 
        interval=1, 
        backupCount=10, 
        encoding='utf-8'
    )
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            file_handler
        ],
        force=True
    )

    for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        logging.getLogger(logger_name).addHandler(file_handler)

    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("qqmusic_api").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    
setup_logging()
logger = logging.getLogger(__name__)

from core.config import CONFIG_FILE_PATH
logger.info(f"--------------------------------------------------")
logger.info(f"System Starting...")
logger.info(f"Using Configuration File: {CONFIG_FILE_PATH}")
logger.info(f"--------------------------------------------------")


from core.config_manager import get_config_manager, reload_config
from core.config import load_config, ensure_security_config, migrate_and_save_config, CONFIG_FILE_PATH
from core.logger import api_log_handler
from app.schemas import LoginRequest, ChangePasswordRequest, UpdateProfileRequest, DownloadRequest, ArtistConfig

# 已移除: event_dispatcher, app_initializer, errors
# (run_in_threadpool 已在文件顶部第 29 行导入，此处重复导入已删除)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        migrate_and_save_config()
        config_instance = get_config_manager()
        config_instance.reload()
        
        init_db()
        
        # Restore logging config (Alembic might have clobbered it)
        setup_logging()
        logger.info("Logging configuration restored after DB migration.")

        # Reload config again now that DB is ready (to load SystemSettings and Normalize YAML)
        config_instance.reload()

        mon_cfg = config_instance.get('monitor', {})
        # Start Scheduler
        scheduler.start()

        # 注册所有循环任务 (新歌增量监控 / 文件完整性 / 自动缓存)
        from app.services.scheduling import register_recurring_jobs
        register_recurring_jobs(scheduler)
        logger.info("周期任务已注册 (新歌监控默认每 6 小时, 可在设置中调整)")

        NotificationService.initialize()
        
        # --- Startup Notification ---
        try:
            from version import get_version_info
            v_info = get_version_info()
            if NotificationService._wecom:
                start_url = config_instance.get('system', {}).get('external_url')
                if not start_url:
                    start_url = "http://localhost:8000"
                
                await NotificationService._wecom.send_text_card(
                    title="🚀 Music Monitor 已启动",
                    description=(
                        f"<div class=\"gray\">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>"
                        f"<div class=\"normal\">版本: {v_info['version']}</div>"
                        f"<div class=\"normal\">构建: {v_info['build_date']}</div>"
                        f"<div class=\"highlight\">系统已准备就绪，数据库状态正常。</div>"
                    ),
                    url=start_url
                )
                logger.info("Startup notification sent.")
        except Exception as e:
            logger.warning(f"Startup notification failed: {e}")


        yield
        # 关闭所有WebSocket连接
        from core.websocket import manager
        await manager.disconnect_all()
        scheduler.shutdown(wait=False)
    except Exception as e:
        import traceback
        import sys
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.stderr)
        print("CRITICAL STARTUP ERROR IN LIFESPAN", file=sys.stderr)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.stderr)
        traceback.print_exc()
        logger.critical(f"Startup failed: {e}", exc_info=True)
        # Re-raise to stop the app
        raise e

app = FastAPI(lifespan=lifespan)
 
# 注册全局异常处理
from app.exceptions import BaseError
# (Request 已在文件顶部第 45 行导入，此处重复导入已删除)

@app.exception_handler(BaseError)
async def business_exception_handler(request: Request, exc: BaseError):
    """
    处理所有自定义业务异常
    """
    status_code = 400
    from app.exceptions import (
        NotFoundError, ValidationError, AuthenticationError, 
        AuthorizationError, RateLimitError
    )
    
    if isinstance(exc, NotFoundError):
        status_code = 404
    elif isinstance(exc, ValidationError):
        status_code = 400
    elif isinstance(exc, (AuthenticationError, AuthorizationError)):
        status_code = 401
    elif isinstance(exc, RateLimitError):
        status_code = 429
        
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    处理所有其他未捕获的异常
    """
    # 记录错误堆栈
    logger.error(f"Unprocessed error: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误，请查看日志",
            "details": {"type": type(exc).__name__, "error": str(exc)}
        }
    )

# 已移除: error_handlers 和 service_container

# Restore Router Imports
from app.routers import auth, media, system, wechat, version
from app.routers.download_history import router as download_history_router
from app.routers.download import router as download_router
from app.routers.metadata import router as metadata_router

app.include_router(auth.router)
# app.include_router(media.router) # Deprecated fully? Wait, media.py still handles playback/download logic.
# We agreed to clean up media.py but keep it for core media operations. 
# Plan says "Clean up and streamline media.py".
# Discovery & Library take over listing/searching.
# Media takes over playback/download.
app.include_router(media.router) 
app.include_router(system.router)
app.include_router(wechat.router)
app.include_router(version.router)
app.include_router(download_history_router)
# app.include_router(download_router) # Redundant with media.py
app.include_router(metadata_router)  # 歌词/封面等元数据 API

# New Routers
from app.routers import discovery, library, subscription, settings
app.include_router(discovery.router)
app.include_router(library.router)
app.include_router(subscription.router)
app.include_router(settings.router)

from app.routers import task_control, websocket
# app.include_router(debug_tasks.router) # Removed

app.include_router(task_control.router)
app.include_router(websocket.router)

# --- Middleware & Static Files Setup ---

# 1. Custom Auth Middleware (Inner)
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    auth_cfg = get_config_manager().get('auth', {})
    if not auth_cfg.get('enabled', False):
        return await call_next(request)

    path = request.url.path
    if path.startswith("/api/"):
        # [Fix C-02] 白名单收敛：仅保留登录流程与企业微信回调等"本就必须公开"的端点。
        # 已移除的放行项及原因：
        #   - /api/audio/            : 任何人可无鉴权拖走全部音频流（已改为需登录会话）
        #   - /api/test_notify_card  : 可被当作通知轰炸放大器
        #   - /api/discovery/probe_qualities : 服务端发起外部请求，存在 SSRF 放大风险
        allowed_paths = [
            "/api/login", "/api/logout", "/api/check_auth",
            "/api/wecom/callback",
            "/api/test_ws", "/api/discovery/cover",
        ]
        if path in allowed_paths:
            pass 
        else:
             try:
                 user = request.session.get("user")
                 if not user:
                     return JSONResponse({"detail": "未授权，请先登录"}, status_code=401)
             except AssertionError:
                 logger.error("Session Middleware not active in auth_middleware scope")
                 return JSONResponse({"detail": "鉴权系统初始化异常"}, status_code=500)
    
    return await call_next(request)

# 2. SessionMiddleware (Outer - added last)
_secret, _updated = ensure_security_config()
if _updated:
    try:
        from core.config import load_config
        get_config_manager().update(load_config())
    except: pass

app.add_middleware(SessionMiddleware, secret_key=_secret, max_age=86400*30) 

# 3. Static Files & Logging
UPLOAD_DIR = "/config/uploads" if CONFIG_FILE_PATH.startswith("/config") else "uploads"
os.makedirs(os.path.join(UPLOAD_DIR, "avatars"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

api_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(api_log_handler)
logging.getLogger("uvicorn").addHandler(api_log_handler)

if os.path.exists("web/dist"):
    app.mount("/assets", StaticFiles(directory="web/dist/assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = f"web/dist/{full_path}"
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse("web/dist/index.html")

if __name__ == "__main__":
    import uvicorn
    # log_config=None 防止 Uvicorn 覆盖我们的 logging 配置
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=1, log_config=None)
