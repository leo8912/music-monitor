"""
主应用入口文件 - FastAPI应用启动和配置
"""
import sys
import os

# --- CRITICAL BOOT DEBUGGING (V2) ---
try:
    print(f"🐍 BOOT DEBUG START | User: {os.getuid()} | Python: {sys.executable}")
    import site
    packages = site.getsitepackages()
    print(f"🐍 site-packages: {packages}")
    
    found = False
    for p in packages:
        if os.path.exists(p):
            try:
                files = os.listdir(p)
                if 'yaml' in files or 'PyYAML' in files:
                    print(f"✅ FOUND 'yaml' in {p}")
                    found = True
                    # Check permissions
                    yp = os.path.join(p, 'yaml')
                    if os.path.exists(yp):
                        st = os.stat(yp)
                        print(f"   Permissions: {oct(st.st_mode)} UID:{st.st_uid}")
                else:
                    print(f"❌ 'yaml' missing in {p}")
            except Exception as e:
                print(f"⚠️ Error reading {p}: {e}")
    
    if not found:
        print("🚨 CRITICAL: PyYAML not found in any site-packages!")
        print("Build verification passed but runtime failed. Checking sys.path...")
        print(sys.path)

except Exception as e:
    print(f"⚠️ Debug crash: {e}")
# -----------------------------

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
import os

# --- CRITICAL BOOT DEBUGGING ---
print(f"🐍 Python Executable: {sys.executable}")
print(f"🐍 Python Version: {sys.version}")
print(f"🐍 User ID: {os.getuid()} Group ID: {os.getgid()}")
print(f"🐍 sys.path: {sys.path}")

try:
    import site
    packages = site.getsitepackages()
    print(f"🐍 Site Packages: {packages}")
    for p in packages:
        if os.path.exists(p):
            print(f"   📂 Listing {p}:")
            try:
                # 只列出前20个，避免刷屏
                print(f"      {os.listdir(p)[:20]}...")
                # 检查 yaml 是否在里面
                if 'yaml' in os.listdir(p) or 'PyYAML' in os.listdir(p):
                    print(f"      ✅ FOUND 'yaml' or 'PyYAML' in {p}")
                    
                    # 检查权限
                    yaml_path = os.path.join(p, 'yaml')
                    if os.path.exists(yaml_path):
                        stat = os.stat(yaml_path)
                        print(f"      🔐 Permissions for {yaml_path}: mode={oct(stat.st_mode)}, uid={stat.st_uid}, gid={stat.st_gid}")
                else:
                    print(f"      ❌ 'yaml' NOT found in {p}")
            except Exception as e:
                print(f"      ⚠️ Error reading {p}: {e}")
except Exception as e:
    print(f"⚠️ Debugging error: {e}")
# -----------------------------

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

from core.database import init_db, SessionLocal, MediaRecord
from app.services.notification import NotificationService
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 创建调度器实例
scheduler = AsyncIOScheduler()

from fastapi import Request, Response, Query
from wechatpy.crypto import WeChatCrypto, PrpCrypto
from wechatpy import parse_message, create_reply
from wechatpy.exceptions import InvalidSignatureException
import xmltodict
from starlette.middleware.sessions import SessionMiddleware
from typing import Optional
from pydantic import BaseModel

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
    ]
)

for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
    logging.getLogger(logger_name).addHandler(file_handler)

logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors.default").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("qqmusic_api").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

from core.config_manager import get_config_manager, reload_config
from core.config import load_config, ensure_security_config, migrate_and_save_config, CONFIG_FILE_PATH
from core.logger import api_log_handler
from app.schemas import LoginRequest, ChangePasswordRequest, UpdateProfileRequest, DownloadRequest, ArtistConfig

# 已移除: event_dispatcher, app_initializer, errors
from starlette.concurrency import run_in_threadpool

@asynccontextmanager
async def lifespan(app: FastAPI):
    migrate_and_save_config()
    config_instance = get_config_manager()
    config_instance.reload()
    init_db()
    
    mon_cfg = config_instance.get('monitor', {})
    # Start Scheduler
    scheduler.start()
    
    # Phase 9: Register Library Scan Jobs
    from app.services.library import LibraryService
    from core.database import AsyncSessionLocal
    
    async def run_library_scan_task(task_type: str = "monitor"):
        """
        Scheduled task for library scanning and enrichment.
        task_type: 'monitor' (frequent, fast) or 'backup' (slow, full)
        """
        import logging
        logger = logging.getLogger("scheduler")
        
        try:
            # We need a synchronous session factory for async context if using run_in_executor
            # But we are in async scheduler, so we can use AsyncSession if we had an async factory
            # Or use sync SessionLocal and wrap it?
            # Actually core/database.py shows SessionLocal is sync? Let's check.
            # Wait, app uses AsyncSession (get_async_session). 
            # I should verify if SessionLocal is async or sync.
            # In media_service imports: from core.database import SessionLocal 
            # and usages: db = SessionLocal(), db.close(). This looks sync.
            # But services expect AsyncSession in some methods?
            # LibraryService methods: async def scan_local_files(self, db: AsyncSession)
            # So I MUST provide an AsyncSession.
            
            from core.database import AsyncSessionLocal 
            
            async with AsyncSessionLocal() as db:
                service = LibraryService()
                
                # Scan - 使用 ScanService
                scan_res = await service.scan_service.scan_local_files(db)
                
                added = 0
                removed = 0
                
                if isinstance(scan_res, dict):
                    added = scan_res.get("new_files_found", 0)
                    removed = scan_res.get("removed_files_count", 0)
                elif isinstance(scan_res, int):
                    added = scan_res
                
                if added > 0 or removed > 0:
                    logger.info(f"[{task_type}] Scan: Found {added} new, removed {removed} records.")
                
                # Enrich - 使用 EnrichmentService (limit depends on type)
                should_enrich = False
                if isinstance(scan_res, dict) and scan_res.get("new_files_found", 0) > 0:
                    should_enrich = True
                elif isinstance(scan_res, int) and scan_res > 0:
                    should_enrich = True
                    
                if should_enrich:
                    logger.info("Triggering auto-enrichment for new files...")
                    try:
                        # 使用新的 auto_enrich_library 方法 (无需传 db, 内部管理)
                        await service.enrichment_service.auto_enrich_library()
                    except Exception as e:
                        logger.error(f"Auto enrichment failed: {e}")
                     
        except Exception as e:
            logger.error(f"Error in library scan task ({task_type}): {e}", exc_info=True)

    # Job 1: Pseudo-Monitoring (Every 60s)
    scheduler.add_job(run_library_scan_task, 'interval', seconds=60, args=['monitor'], id='job_library_monitor')
    
    # Job 2: Backup Scan (Every 30m)
    scheduler.add_job(run_library_scan_task, 'interval', minutes=30, args=['backup'], id='job_library_backup')
    
    # 已移除: PLUGINS 监控任务 (使用 music_providers 替代)
            
    from app.services.media_service import check_file_integrity
    scheduler.add_job(
        check_file_integrity,
        'interval',
        hours=24,
        id="job_file_integrity",
        replace_existing=True
    )
    logger.info("已调度文件完整性检查任务，每 24 小时执行一次")

    # 已移除: cleanup_cache 任务
    
    from app.services.media_service import auto_cache_recent_songs
    scheduler.add_job(
        auto_cache_recent_songs,
        'interval',
        minutes=30,
        id="job_auto_cache",
        replace_existing=True
    )
    logger.info(f"已调度自动缓存任务，每 30 分钟执行一次")
    
    NotificationService.initialize()

    yield
    # 关闭所有WebSocket连接
    from core.websocket import manager
    await manager.disconnect_all()
    scheduler.shutdown(wait=False)

app = FastAPI(lifespan=lifespan)
 
# 注册全局异常处理
from app.exceptions import BaseError
from fastapi import Request

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
from app.routers import discovery, library, subscription
app.include_router(discovery.router)
app.include_router(library.router)
app.include_router(subscription.router)

# --- Middleware & Static Files Setup ---

# 1. Custom Auth Middleware (Inner)
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    auth_cfg = get_config_manager().get('auth', {})
    if not auth_cfg.get('enabled', False):
        return await call_next(request)

    path = request.url.path
    if path.startswith("/api/"):
        allowed_paths = [
            "/api/login", "/api/logout", "/api/check_auth", 
            "/api/wecom/callback", "/api/mobile/metadata",
            "/api/test_ws", "/api/discovery/probe_qualities", "/api/discovery/cover"
        ]
        if path in allowed_paths or path.startswith("/api/test_notify_card") or path.startswith("/api/audio/"):
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
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=1)
