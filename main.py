import asyncio
import logging
import yaml
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from datetime import datetime
from datetime import datetime
import collections
from urllib.parse import quote

from core.database import init_db, SessionLocal, MediaRecord, get_db
from core.plugins import PLUGINS
from core.scheduler import scheduler
from core.wechat import FixedWeChatCrypto
from app.services.media_service import process_media_item, run_check, find_artist_ids
from notifiers.wecom import WeComNotifier
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
# Create handler explicitly to attach to uvicorn
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

# Attach file handler to Uvicorn loggers to capture startup/errors in file
for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
    logging.getLogger(logger_name).addHandler(file_handler)

# Suppress noisy logs from third-party libraries
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors.default").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("qqmusic_api").setLevel(logging.WARNING)
logging.getLogger("watchfiles").setLevel(logging.WARNING)

# Trigger Reload
logger = logging.getLogger(__name__)

# Plugin Registry


from core.config import config, load_config, ensure_security_config, migrate_and_save_config, CONFIG_FILE_PATH
from core.logger import api_log_handler
from app.schemas import LoginRequest, ChangePasswordRequest, UpdateProfileRequest, DownloadRequest, ArtistConfig








from core.event_bus import event_bus
from notifiers.wecom import WeComNotifier
from notifiers.telegram import TelegramNotifier
from starlette.concurrency import run_in_threadpool

# Initialize Notifiers
wecom_notifier = WeComNotifier("", "", "")
telegram_notifier = TelegramNotifier("", "") 

def update_notifier_config(cfg):
    notify_cfg = cfg.get('notify', {})
    
    # WeCom
    wecom_cfg = notify_cfg.get('wecom', {})
    if wecom_cfg.get('enabled') and wecom_notifier:
        wecom_notifier.corp_id = wecom_cfg.get('corpid')
        wecom_notifier.secret = wecom_cfg.get('corpsecret')
        wecom_notifier.agent_id = wecom_cfg.get('agentid')
        
    # Telegram
    tg_cfg = notify_cfg.get('telegram', {})
    if tg_cfg.get('enabled') and telegram_notifier:
        telegram_notifier.token = tg_cfg.get('bot_token')
        telegram_notifier.chat_id = tg_cfg.get('chat_id')

async def handle_new_content(media):
    message_text = (
        f"🎵 新歌发布: {media.title}\n"
        f"👤 歌手: {media.author}\n"
        f"💿 专辑: {media.album or '单曲'}\n"
        f"🔗 链接: {media.url}\n"
        f"📅 时间: {media.publish_time}"
    )
    
    # Use custom description if provided (for batch summaries)
    if hasattr(media, 'custom_description') and media.custom_description:
        message_text = media.custom_description
    
    # 1. WeCom
    if config.get('notify', {}).get('wecom', {}).get('enabled'):
        try:
             target_url = media.url
             # Use external_url if configured
             ext_url = config.get('global', {}).get('external_url')
             if ext_url and ext_url.startswith('http'):
                 # Ensure no trailing slash
                 ext_url = ext_url.rstrip('/')
                 # Construct deep link
                 target_url = f"{ext_url}?source={media.source}&songId={media.media_id}"

             # Prepare description for News card (simpler is better for News card description as it's small text under title)
             # But user wants a specific format?
             # User image shows: "Start playing... User: ... IP: ... Time: ..."
             # My current message_text is:
             # 🎵 新歌发布: Title
             # 👤 歌手: Artist
             # 💿 专辑: Album
             # 📅 时间: Time
             # This is fine for description.
             
             await wecom_notifier.send_news_message(
                 title=f"🎵 新歌发布: {media.title}",
                 description=message_text,
                 url=target_url,
                 pic_url=getattr(media, 'cover', None) or getattr(media, 'cover_url', '') 
             )
        except Exception as e:
            logger.error(f"WeCom notify failed: {e}")

    # 2. Telegram
    if config.get('notify', {}).get('telegram', {}).get('enabled'):
         try:
             await run_in_threadpool(
                telegram_notifier.send_message,
                message_text,
                image_url=media.cover_url
             )
         except Exception as e:
            logger.error(f"Telegram notify failed: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Migrate legacy config first
    migrate_and_save_config()
    
    # Load config
    config.update(load_config())
    
    # Initialize DB
    init_db()
    
    # Init plugins with config
    mon_cfg = config.get('monitor', {})
    
    # Start Scheduler
    scheduler.start()
    
    # Schedule jobs
    for name, plugin_cls in PLUGINS.items():
        if name in mon_cfg and mon_cfg[name].get('enabled'):
            interval = mon_cfg[name].get('interval', 60)
            scheduler.add_job(
                run_check, 
                'interval', 
                minutes=interval, 
                args=[name], # Remove config arg
                id=f"job_{name}",
                replace_existing=True
            )
            logger.info(f"已调度 {name} 任务，每 {interval} 分钟执行一次")
            
    # Schedule integrity check (daily)
    from app.services.media_service import check_file_integrity
    scheduler.add_job(
        check_file_integrity,
        'interval',
        hours=24,
        id="job_file_integrity",
        replace_existing=True
    )
    logger.info("已调度文件完整性检查任务，每 24 小时执行一次")

    # Schedule cache cleanup (daily)
    from core.cleanup import cleanup_cache
    scheduler.add_job(
        cleanup_cache,
        'interval',
        hours=24,
        id="job_cache_cleanup",
        replace_existing=True
    )
    logger.info(f"已调度缓存清理任务，每 24 小时执行一次")
    
    # Schedule auto-cache (every 30 mins)
    from app.services.media_service import auto_cache_recent_songs
    scheduler.add_job(
        auto_cache_recent_songs,
        'interval',
        minutes=30,
        id="job_auto_cache",
        replace_existing=True
    )
    # Trigger once on startup (optional, but good for immediate effect)
    # We can use run_date=datetime.now() for one-off but we want interval.
    # We can just add another job for 'date' trigger now() but scheduler start() is async.
    # It will run in 30 mins. That's fine.
    logger.info(f"已调度自动缓存任务，每 30 分钟执行一次")
    
    # Initial Notify Init
    update_notifier_config(config)
    
    # Subscribe to events
    event_bus.subscribe("new_content", handle_new_content)

    yield
    
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

from app.routers import auth
from app.routers import media
from app.routers import system
from app.routers import wechat
from app.routers import version
app.include_router(auth.router)
app.include_router(media.router)
app.include_router(system.router)
app.include_router(wechat.router)
app.include_router(version.router)

# Mount uploads directory
import os
if CONFIG_FILE_PATH.startswith("/config"):
    UPLOAD_DIR = "/config/uploads"
else:
    UPLOAD_DIR = "uploads"
    
os.makedirs(os.path.join(UPLOAD_DIR, "avatars"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")



# Add Middleware (Session)
# Note: In production, secret_key should be robust.
# We delay reading config until lifespan, but Middleware init happens at creation.
# So we read config once here solely for secret_key, or use a default.
# To keep it simple, we re-read config or just use a placeholder if not loaded yet.
# Actually, loading it here is safer.
# Custom Auth Middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Check if auth enabled
    auth_cfg = config.get('auth', {})
    if not auth_cfg.get('enabled', False):
        return await call_next(request)

    path = request.url.path
    
    # White list
    # /api/login, /api/check_auth, /assets (static), / (spa index)
    if path.startswith("/api/"):
        if path in ["/api/login", "/api/logout", "/api/check_auth", "/api/wecom/callback"] or path.startswith("/api/test_notify_card"):
            pass # Allowed
        else:
             try:
                 user = request.session.get("user")
                 if not user:
                     return JSONResponse({"detail": "未授权，请先登录"}, status_code=401)
             except AssertionError:
                 # Session middleware issue fallback
                 logger.error("Session Middleware not active")
                 return JSONResponse({"detail": "鉴权服务异常"}, status_code=500)
    
    response = await call_next(request)
    return response

# Add Middleware (Session) - Must be added last to run first!

# Security: Rotate secret if default
_secret, _updated = ensure_security_config()
if _updated:
    # If updated, reload config object globally
    try:
        config.update(load_config()) 
    except: pass

app.add_middleware(SessionMiddleware, secret_key=_secret, max_age=86400*30) # 30 days

# Allow CORS for dev (optional, mostly relevant if running frontend separately)

api_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(api_log_handler)
logging.getLogger("uvicorn").addHandler(api_log_handler)



# Mount Frontend (only if exists, for production)
# In Docker, we copy to /app/web/dist
if os.path.exists("web/dist"):
    app.mount("/assets", StaticFiles(directory="web/dist/assets"), name="assets")
    
    # Catch-all for SPA
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # API routes are handled above.
        file_path = f"web/dist/{full_path}"
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        return FileResponse("web/dist/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
