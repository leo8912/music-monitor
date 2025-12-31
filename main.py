import asyncio
import logging
import yaml
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from datetime import datetime
import collections

from core.database import init_db, SessionLocal, MediaRecord, get_db
from core.event_bus import event_bus
from domain.models import MediaInfo
from plugins.netease import NeteaseMonitor
from plugins.qqmusic import QQMusicMonitor
from plugins.bilibili import BilibiliMonitor, BilibiliSearcher
from notifiers.wecom import WeComNotifier
from fastapi import Request, Response, Query
from wechatpy.crypto import WeChatCrypto
from wechatpy import parse_message, create_reply
from wechatpy.exceptions import InvalidSignatureException
import xmltodict
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# Suppress noisy logs from third-party libraries
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors.default").setLevel(logging.ERROR) # Suppress "Run time of job ... was missed"
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("qqmusic_api").setLevel(logging.WARNING)

# Trigger Reload
logger = logging.getLogger(__name__)

# Plugin Registry
PLUGINS = {
    'netease': NeteaseMonitor,
    'qqmusic': QQMusicMonitor
    # 'bilibili': BilibiliMonitor # Removed 
}

# Global searcher
bilibili_searcher = BilibiliSearcher()
scheduler = AsyncIOScheduler()
config = {}

def load_config():
    with open("config.yaml", "r", encoding='utf-8') as f:
        return yaml.safe_load(f)

# --- Auth Models ---
class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

import secrets
import re

def ensure_security_config():
    """Ensure secret_key is secure and not default."""
    try:
        with open("config.yaml", "r", encoding='utf-8') as f:
            content = f.read()
        
        # Check current secret
        match = re.search(r'secret_key:\s*["\']?([^"\']+)["\']?', content)
        if match:
            current_secret = match.group(1).strip()
            # If default or weak
            if current_secret in ["secret_key_for_session_encryption", "default_secret_key", "CHANGE_THIS_TO_RANDOM_SECRET"]:
                new_secret = secrets.token_urlsafe(32)
                logger.warning(f"Detected weak secret_key. Rotated to new random key.")
                
                # Replace in content (preserve whitespace/comments)
                new_content = re.sub(
                    r'(secret_key:\s*)(["\']?)([^"\']+)(["\']?)', 
                    f'\\1"{new_secret}"', 
                    content
                )
                
                with open("config.yaml", "w", encoding='utf-8') as f:
                    f.write(new_content)
                
                return new_secret, True
            return current_secret, False
    except Exception as e:
        logger.error(f"Security config check failed: {e}")
    return "default_secret_key", False

async def process_media_item(media: MediaInfo, db: Session):
    """Check if media is new, save to DB, and notify."""
    # 1. Check exact match (same source, same ID)
    # 1. Check exact match (same source, same ID)
    key = media.unique_key()
    existing = db.query(MediaRecord).filter_by(unique_key=key).first()
    if existing:
        # Check if we need to backfill cover OR urls
        updated = False
        if not existing.cover and media.cover_url:
             existing.cover = media.cover_url
             updated = True
             
        if not existing.url and media.url:
             existing.url = media.url
             updated = True
        
        # Check trial_url (Bilibili link)
        if hasattr(existing, 'trial_url') and not existing.trial_url:
             search_keyword = f"{existing.author} {existing.title}"
             logger.info(f"Adding Bilibili link for: {search_keyword}")
             trial_link = await bilibili_searcher.search_video(search_keyword)
             if trial_link:
                 existing.trial_url = trial_link
                 updated = True
                 logger.info(f"Updated Bilibili link for: {media.title} -> {trial_link}")
             else:
                 logger.warning(f"Bilibili search returned None for: {search_keyword}")
        
        if updated:
             db.commit()
             logger.info(f"Updated metadata for existing record: {media.title}")
        return

    # 2. Check cross-platform duplicate (same title, same artist, same album)
    # This strictly matches metadata. "Remix" versions usu. have diff album or diff title.
    query = db.query(MediaRecord).filter(
        MediaRecord.title == media.title,
        MediaRecord.author == media.author,
        MediaRecord.media_type == media.type.value
    )
    
    if media.album:
         query = query.filter(MediaRecord.album == media.album)
         
    cross_platform_dup = query.first()

    if cross_platform_dup:
        logger.info(f"跳过重复内容 (跨平台): {media.title} (已存在于 {cross_platform_dup.source})")
        return

    logger.info(f"发现新内容: {media.title} ({key})")
    
    # Enrich with Bilibili search
    # We search for "Artist Title"
    search_keyword = f"{media.author} {media.title}"
    trial_link = await bilibili_searcher.search_video(search_keyword)
    if trial_link:
        logger.info(f"找到 Bilibili 试听链接: {trial_link}")
        media.trial_url = trial_link

    # Save to DB
    record = MediaRecord(
        unique_key=key,
        source=media.source,
        media_type=media.type.value,
        media_id=media.id,
        title=media.title,
        author=media.author,
        album=media.album,
        cover=media.cover_url, 
        url=media.url,  # Save URL
        trial_url=media.trial_url, # Save Trial URL
        publish_time=media.publish_time,
        is_pushed=False
    )
    db.add(record)
    db.commit()
    
    # Notify
    await event_bus.publish("new_content", media)
    
    # Mark as pushed
    record.is_pushed = True
    record.push_time = datetime.now()
    db.commit()

async def run_check(plugin_name: str, config: dict):
    """Job to run a specific plugin check."""
    logger.info(f"开始检查任务: {plugin_name}...")
    
    cfg = config['monitor'].get(plugin_name, {})
    if not cfg.get('enabled'):
        return

    plugin_cls = PLUGINS.get(plugin_name)
    if not plugin_cls:
        if plugin_name != "bilibili":
            logger.error(f"未找到插件: {plugin_name}")
        return

    plugin = plugin_cls()
    users = cfg.get('users', [])
    
    # Use a new DB session for this job
    db = SessionLocal()
    try:
        for user in users:
            uid = user['id']
            uname = user.get('name', uid)
            try:
                items = await plugin.get_new_content(uid, uname)
                for item in items:
                    await process_media_item(item, db)
            except Exception as e:
                logger.error(f"检查用户 {uname}({uid}) ({plugin_name}) 时出错: {e}")
    finally:
        db.close()
    
    logger.info(f"检查完成: {plugin_name}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global config
    init_db()
    config = load_config()
    
def update_notifier_config(current_config: dict):
    """Re-initializes notifiers based on the current config."""
    # Clear existing subscribers to avoid duplicates
    event_bus.clear_subscribers("new_content")

    wecom_cfg = current_config['notify'].get('wecom', {})
    if wecom_cfg.get('enabled'):
        notifier = WeComNotifier(
            corp_id=wecom_cfg['corp_id'],
            secret=wecom_cfg['secret'],
            agent_id=wecom_cfg['agent_id']
        )
        event_bus.subscribe("new_content", notifier.send)
        logger.info("企业微信通知器已初始化")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load config
    global config
    config = load_config()
    
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
                args=[name, config], 
                id=f"job_{name}",
                replace_existing=True
            )
            logger.info(f"已调度 {name} 任务，每 {interval} 分钟执行一次")
    
    # Initial Notify Init
    update_notifier_config(config)

    yield
    
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

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
        if path in ["/api/login", "/api/logout", "/api/check_auth", "/api/wecom/callback"]:
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
# Add Middleware (Session) - Must be added last to run first!
# Security: Rotate secret if default
_secret, _updated = ensure_security_config()
if _updated:
    # If updated, reload config object globally
    try:
        config = load_config() 
    except: pass

app.add_middleware(SessionMiddleware, secret_key=_secret, max_age=86400*30) # 30 days

# --- Auth Endpoints ---
@app.post("/api/login")
async def login(req: LoginRequest, request: Request):
    auth_cfg = config.get('auth', {})
    if not auth_cfg.get('enabled', False):
         return {"message": "鉴权已禁用"}
         
    if req.username == auth_cfg.get('username') and req.password == auth_cfg.get('password'):
        request.session["user"] = req.username
        return {"message": "登录成功"}
    
    raise HTTPException(status_code=401, detail="账号或密码错误")

@app.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}

@app.post("/api/change_password")
async def change_password(req: ChangePasswordRequest, request: Request):
    global config
    auth_cfg = config.get('auth', {})
    if not auth_cfg.get('enabled', False):
         raise HTTPException(status_code=400, detail="Auth not enabled")
    
    # 1. Verify old password
    if req.old_password != auth_cfg.get('password'):
        raise HTTPException(status_code=401, detail="旧密码错误")
    
    # 2. Update config file
    try:
        with open("config.yaml", "r", encoding='utf-8') as f:
            content = f.read()
            
        # Regex replace password
        # Look for password: "..." inside auth block is hard with simple regex 
        # But assuming standard indentation from previous view: "  password: "..."
        # We'll use a specific regex that assumes 'password:' key
        
        # Check if password matches old password to be safe
        # Pattern: password:\s*["']?OLD_PASSWORD["']?
        old_esc = re.escape(req.old_password)
        pattern = fr'(password:\s*)(["\']?)({old_esc})(["\']?)'
        
        if not re.search(pattern, content):
             logger.error("Could not find password in config file to replace")
             # Fallback: simple replace if regex fails (risky if password appears elsewhere)
             # Let's try to be precise with indentation if possible or just report error
             raise Exception("Config file password pattern mismatch")

        new_content = re.sub(
            pattern,
            f'\\1"{req.new_password}"',
            content,
            count=1 # Only replace first occurrence (should be ok)
        )
        
        with open("config.yaml", "w", encoding='utf-8') as f:
            f.write(new_content)
            
        # 3. Reload global config
        config = load_config()
        
        # 4. Logout user
        request.session.clear()
        
        return {"message": "密码修改成功，请重新登录"}
        
    except Exception as e:
        logger.error(f"Failed to change password: {e}")
        raise HTTPException(status_code=500, detail=f"修改失败: {str(e)}")

@app.get("/api/check_auth")
async def check_auth(request: Request):
    auth_cfg = config.get('auth', {})
    
    # Debug logging
    user = request.session.get("user")
    is_enabled = auth_cfg.get('enabled', False)
    raw_cookie = request.headers.get("cookie", "NO_COOKIE")
    logger.info(f"[AuthCheck] Enabled={is_enabled}, User={user}, Cookie={raw_cookie}")

    if not is_enabled:
        return JSONResponse(
            content={"authenticated": True, "user": "admin", "enabled": False},
            headers={"Cache-Control": "no-store"}
        )
        
    return JSONResponse(
        content={"authenticated": bool(user), "user": user, "enabled": True},
        headers={"Cache-Control": "no-store"}
    )

# Allow CORS for dev (optional, mostly relevant if running frontend separately)

@app.get("/api/status")
async def get_status():
    jobs = scheduler.get_jobs()
    job_info = [{"id": j.id, "next_run": j.next_run_time} for j in jobs]
    return {"status": "running", "jobs": job_info}

from pydantic import BaseModel
from typing import Optional
import pyncm.apis.cloudsearch
from qqmusic_api.search import search_by_type, SearchType

class ArtistConfig(BaseModel):
    name: str
    id: Optional[str] = None
    source: Optional[str] = None

async def find_artist_ids(name):
    """Find artist IDs in both Netease and QQ Music."""
    results = []
    
    # Netease
    try:
        data = pyncm.apis.cloudsearch.GetSearchResult(name, stype=100)
        if 'result' in data and 'artists' in data['result'] and data['result']['artists']:
            first = data['result']['artists'][0]
            # Verify name match to avoid weird partial matches? 
            # For now accept the top result.
            results.append({
                "source": "netease", 
                "id": str(first['id']), 
                "name": first['name'],
                "avatar": first.get('picUrl', '')
            })
            logger.info(f"Smart Search Netease: Found {first['name']} ({first['id']})")
    except Exception as e:
        logger.error(f"Netease search failed: {e}")

    # QQ Music
    try:
        data = await search_by_type(name, SearchType.SINGER)
        if data:
            first = data[0]
            # QQ keys: mid, singerName/name
            mid = first.get('mid', first.get('singerMID'))
            param_name = first.get('name', first.get('singerName'))
            avatar = ""
            if mid:
                avatar = f"https://y.gtimg.cn/music/photo_new/T001R300x300M000{mid}.jpg"
                results.append({
                    "source": "qqmusic", 
                    "id": mid, 
                    "name": param_name,
                    "avatar": avatar
                })
                logger.info(f"Smart Search QQ: Found {param_name} ({mid})")
    except Exception as e:
        logger.error(f"QQ search failed: {e}")
        
    return results

@app.get("/api/artists")
async def get_artists():
    """Get all monitored artists from config."""
    artists = []
    mon_cfg = config.get('monitor', {})
    
    # Netease
    if mon_cfg.get('netease', {}).get('enabled'):
        for u in mon_cfg['netease'].get('users', []):
            artists.append({
                "name": u.get('name', u['id']), 
                "id": str(u['id']), 
                "source": "netease",
                "avatar": u.get('avatar', 'https://p1.music.126.net/6y-UleORITEDbvrOLV0Q8A==/5639395138885805.jpg') # Default Netease avatar or empty
            })
            
    # QQMusic
    if mon_cfg.get('qqmusic', {}).get('enabled'):
        for u in mon_cfg['qqmusic'].get('users', []):
            # Auto-construct QQ avatar if missing
            avatar = u.get('avatar', '')
            if not avatar and u['id']:
                avatar = f"https://y.gtimg.cn/music/photo_new/T001R300x300M000{u['id']}.jpg"
                
            artists.append({
                "name": u.get('name', u['id']), 
                "id": u['id'], 
                "source": "qqmusic",
                "avatar": avatar
            })
            
    return artists

@app.post("/api/artists")
async def add_artist(artist: ArtistConfig):
    """Add new artist. If id/source missing, perform smart search."""
    # 1. Automatic Search Mode
    if not artist.id or not artist.source:
        found = await find_artist_ids(artist.name)
        if not found:
            raise HTTPException(status_code=404, detail="Artist not found on any platform")
        
        added = []
        for item in found:
            # Add each found artist
            source_cfg = config['monitor'].get(item['source'])
            if not source_cfg: continue
            
            # Check dup
            exists = False
            for u in source_cfg['users']:
                if str(u['id']) == str(item['id']):
                    exists = True
                    # Update avatar if missing?
                    if not u.get('avatar') and item.get('avatar'):
                         u['avatar'] = item['avatar']
                    break
            
            if not exists:
                new_user = {"id": item['id'], "name": artist.name}
                if item.get('avatar'):
                    new_user['avatar'] = item['avatar']
                source_cfg['users'].append(new_user) 
                added.append(f"{item['source']}:{item['name']}")
        
        if not added:
             # Just return success if simply updated/already exists, don't error
             # But if nothing was processed, that's different.
             pass 

        # Save
        with open("config.yaml", "w", encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
            
        return {"status": "success", "message": f"Added/Updated {', '.join(added) or 'Existing artists'}"}

    # 2. Manual Mode (Legacy)
    source_cfg = config['monitor'].get(artist.source)
    if not source_cfg:
        raise HTTPException(status_code=400, detail="Invalid source")
        
    # Check duplicate
    for u in source_cfg['users']:
        if u['id'] == artist.id:
            raise HTTPException(status_code=400, detail="Artist already exists")
            
    source_cfg['users'].append({"id": artist.id, "name": artist.name})
    
    # Save to file
    with open("config.yaml", "w", encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
        
    return {"status": "success", "artist": artist}

@app.delete("/api/artists/{source}/{id}")
async def delete_artist(source: str, id: str):
    """Remove artist from config and save."""
    source_cfg = config['monitor'].get(source)
    if not source_cfg:
        raise HTTPException(status_code=404, detail="Source not found")
        
    # Filter out
    original_len = len(source_cfg['users'])
    source_cfg['users'] = [u for u in source_cfg['users'] if u['id'] != id]
    
    if len(source_cfg['users']) == original_len:
        raise HTTPException(status_code=404, detail="Artist not found")

    # Save
    with open("config.yaml", "w", encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
        
    return {"status": "success"}


# Simple in-memory cache for playback URLs
# Key: {source}:{id}, Value: {url, timestamp}
playback_cache = {}

@app.get("/api/play/{source}/{id}")
async def play_proxy(source: str, id: str):
    """
    Proxy to fetch direct playback URL using internal plugins.
    Fallbacks to official page if failed.
    """
    # Check cache (valid for 20 mins)
    cache_key = f"{source}:{id}"
    if cache_key in playback_cache:
        cached = playback_cache[cache_key]
        if (datetime.now() - cached['time']).total_seconds() < 1200:
            return RedirectResponse(cached['url'])

    play_url = None
    
    try:
        if source == 'netease':
            # pyncm is synchronous
            # GetTrackAudio returns {'data': [{'id': x, 'url': 'http...', ...}], 'code': 200}
            res = pyncm.apis.track.GetTrackAudio([id])
            if res.get('code') == 200 and res.get('data'):
                 play_url = res['data'][0].get('url')
                 
        elif source == 'qqmusic':
            # qqmusic_api is async
            # get_song_urls returns {mid: url} or empty dict
            try:
                from qqmusic_api import song
                # get_song_urls takes a list of mids
                urls = await song.get_song_urls([id])
                if urls and id in urls:
                    play_url = urls[id]
            except Exception as e:
                logger.error(f"QQMusic lib error: {e}")

    except Exception as e:
        logger.error(f"Internal lib fetch error: {e}")

    if play_url:
        # Cache successful result
        playback_cache[cache_key] = {
            'url': play_url,
            'time': datetime.now()
        }
        return RedirectResponse(play_url)

    # Fallback: finding the DB record to get the official URL
    db = SessionLocal()
    try:
        record = db.query(MediaRecord).filter_by(source=source, media_id=id).first()
        if record and record.url:
            return RedirectResponse(record.url)
            
        # Last resort fallback
        if source == 'netease':
            return RedirectResponse(f"https://music.163.com/#/song?id={id}")
        elif source == 'qqmusic':
            return RedirectResponse(f"https://y.qq.com/n/ryqq/songDetail/{id}")
            
        return JSONResponse({"error": "Playback link not found"}, status_code=404)
    finally:
        db.close()
@app.get("/api/settings")
async def get_settings():
    """Get global configuration."""
    return config

@app.post("/api/settings")
async def update_settings(new_config: dict):
    """Update global configuration."""
    global config
    try:
        # Validate structure roughly
        if 'global' not in new_config or 'monitor' not in new_config or 'notify' not in new_config:
            raise HTTPException(status_code=400, detail="Invalid config structure")
            
        # Update memory
        config.update(new_config)
        
        # Save to file
        with open("config.yaml", "w", encoding='utf-8') as f:
            yaml.safe_dump(config, f, allow_unicode=True, default_flow_style=False)
            
        logger.info("Configuration updated via API")
        return {"status": "success", "message": "Settings saved"}
    except Exception as e:
        logger.error(f"Failed to save settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# Log Buffer for API
class APILogHandler(logging.Handler):
    def __init__(self, capacity=100):
        super().__init__()
        self.capacity = capacity
        self.buffer = collections.deque(maxlen=capacity)
    
    def emit(self, record):
        try:
            msg = self.format(record)
            self.buffer.append({
                "time": datetime.fromtimestamp(record.created).strftime('%H:%M:%S'),
                "level": record.levelname,
                "message": msg,
                "source": record.name
            })
        except Exception:
            self.handleError(record)

api_log_handler = APILogHandler()
api_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(api_log_handler)
logging.getLogger("uvicorn").addHandler(api_log_handler)

@app.get("/api/logs")
async def get_logs():
    """Get recent logs."""
    return list(api_log_handler.buffer)


@app.get("/api/match_bilibili")
async def match_bilibili(artist: str, title: str):
    """
    Search Bilibili for the MV/Audio and return the BVID and URL.
    """
    # Optimized keyword: Title first, then Artist. Added 'MV' hint? 
    # Let's try "Title Artist" first as it's cleaner.
    keyword = f"{title} {artist}"
    logger.info(f"API Request: Matching Bilibili for {keyword}")
    try:
        url = await bilibili_searcher.search_video(keyword)
        logger.info(f"Search Result: {url}")
        
        if url:
            # Extract BVID (BVxxxxxx) or avID
            import re
            bvid = None
            
            # Try BV match
            match_bv = re.search(r"(BV\w+)", url)
            if match_bv:
                bvid = match_bv.group(1)
            
            # If no BV, try AV? (bilibili player supports aid=xxx)
            # But the iframe code uses bvid. Let's strictly return headers if found.
            
            if bvid:
                return {"url": url, "bvid": bvid}
            else:
                logger.warning(f"Could not extract BVID from URL: {url}")
                return JSONResponse({"error": "BVID not found"}, status_code=404)
        return JSONResponse({"error": "Not found"}, status_code=404)
                
    except Exception as e:
        logger.error(f"Bilibili match error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
        
@app.post("/api/test_notify/{channel}")
async def test_notify(channel: str):
    """Send a test notification to the specified channel."""
    try:
        # Load fresh config logic
        notify_cfg = config.get('notify', {})
        
        if channel == 'wecom':
            cfg = notify_cfg.get('wecom', {})
            notifier = WeComNotifier(
                corp_id=cfg.get('corp_id'),
                secret=cfg.get('secret'),
                agent_id=cfg.get('agent_id')
            )
            await notifier.send_test_message()
            return {"status": "success", "message": "WeCom test message sent"}
            
        elif channel == 'telegram':
            from notifiers.telegram import TelegramNotifier
            cfg = notify_cfg.get('telegram', {})
            notifier = TelegramNotifier(
                bot_token=cfg.get('bot_token'),
                chat_id=cfg.get('chat_id')
            )
            await notifier.send_test_message()
            return {"status": "success", "message": "Telegram test message sent"}
            
        else:
            raise HTTPException(status_code=400, detail="Unknown channel")
            
    except Exception as e:
        logger.error(f"Test notify failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/check_notify_status/{channel}")
async def check_notify_status(channel: str):
    """Check connectivity status for notification channel."""
    try:
        notify_cfg = config.get('notify', {})
        if channel == 'wecom':
            cfg = notify_cfg.get('wecom', {})
            notifier = WeComNotifier(
                corp_id=cfg.get('corp_id'),
                secret=cfg.get('secret'),
                agent_id=cfg.get('agent_id')
            )
            ok = await notifier.check_connectivity()
            return {"status": "ok" if ok else "error", "connected": ok}
            
        elif channel == 'telegram':
            from notifiers.telegram import TelegramNotifier
            cfg = notify_cfg.get('telegram', {})
            notifier = TelegramNotifier(
                bot_token=cfg.get('bot_token'),
                chat_id=cfg.get('chat_id')
            )
            ok = await notifier.check_connectivity()
            return {"status": "ok" if ok else "error", "connected": ok}
            
        return {"status": "error", "connected": False}
    except Exception as e:
         return {"status": "error", "connected": False, "detail": str(e)}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register Event Listeners

    
    # Initialize Notification
    # ...
    
    # Initialize Scheduler
    scheduler.start()
    init_db()
    
    # Schedule Jobs
    # ...

# ... (omitted delete_artist)

@app.get("/api/history")
async def get_history(limit: int = 100):
    db = SessionLocal()
    try:
        # Get active artists from config for filtering
        active_names = set()
        for source in ['netease', 'qqmusic', 'bilibili']:
             cfg = config.get('monitor', {}).get(source, {})
             if cfg.get('enabled'):
                 for u in cfg.get('users', []):
                     active_names.add(u.get('name', ''))
        
        # Fetch more to handle filtering
        records = db.query(MediaRecord).order_by(MediaRecord.publish_time.desc()).limit(limit * 2).all()
        
        filtered = []
        seen_keys = set()
        
        for r in records:
            # 1. Deduplication (Title + Author)
            # Normalize title for dedup (remove spaces, lowercase)
            norm_title = "".join(filter(str.isalnum, r.title or "")).lower()
            norm_author = "".join(filter(str.isalnum, r.author or "")).lower()
            dedup_key = f"{norm_title}_{norm_author}"
            
            if dedup_key in seen_keys:
                continue
            
            # 2. Filtering (Only show monitored artists)
            # Check if any active artist name is part of the record's author string
            is_relevant = False
            for name in active_names:
                if name and name in (r.author or ""):
                    is_relevant = True
                    break
            
            if not is_relevant:
                continue
                
            seen_keys.add(dedup_key)
            filtered.append(r)
            
            if len(filtered) >= limit:
                break
                
        return filtered
    finally:
        db.close()

@app.post("/api/check/{plugin_name}")
async def trigger_check(plugin_name: str):
    if plugin_name not in PLUGINS and plugin_name != "bilibili":
         raise HTTPException(status_code=404, detail="Plugin not found")
    
    # Run in background
    asyncio.create_task(run_check(plugin_name, config))

# --- WeCom Interaction ---

async def handle_wecom_command(text: str) -> str:
    """Handle interactive commands from WeCom."""
    try:
        logger.info(f"Processing WeCom command: {text}")
        text = text.strip()
        
        # 1. Delete Command (删除/remove/delete)
        if text.startswith(("删除", "remove", "delete")):
            # Extract name
            parts = text.split(" ", 1)
            if len(parts) < 2 and len(text) > 2:
                # Handle "删除周杰伦" (no space)
                name = text.replace("删除", "").replace("remove", "").replace("delete", "").strip()
            elif len(parts) >= 2:
                name = parts[1].strip()
            else:
                return "❌ 请指定要删除的歌手，例如：删除周杰伦"
            
            # Search and remove from config
            removed_count = 0
            mon_cfg = config.get('monitor', {})
            for source in ['netease', 'qqmusic']:
                if source in mon_cfg:
                    users = mon_cfg[source].get('users', [])
                    initial_len = len(users)
                    mon_cfg[source]['users'] = [u for u in users if u.get('name') != name]
                    if len(mon_cfg[source]['users']) < initial_len:
                        removed_count += 1
            
            if removed_count > 0:
                with open("config.yaml", "w", encoding='utf-8') as f:
                     yaml.dump(config, f, allow_unicode=True)
                return f"✅ 已删除歌手: {name} (从 {removed_count} 个来源移除)"
            else:
                return f"⚠️ 未找到歌手: {name}"

        # 2. Add Command (Default) -> "周杰伦"
        else:
            name = text
            # Reuse find_artist_ids
            found = await find_artist_ids(name)
            if not found:
                 return f"⚠️ 未找到歌手: {name}，请检查名字是否正确。"
            
            # Add to config
            added_names = []
            for item in found:
                source_cfg = config['monitor'].get(item['source'])
                if not source_cfg: continue
                
                # Check exist
                exists = False
                for u in source_cfg.get('users', []):
                    if str(u['id']) == str(item['id']):
                        exists = True
                        break
                
                if not exists:
                    new_user = {"id": item['id'], "name": item['name']}
                    if item.get('avatar'): new_user['avatar'] = item['avatar']
                    source_cfg.setdefault('users', []).append(new_user)
                    added_names.append(f"{item['source']}:{item['name']}")
                    
            if added_names:
                with open("config.yaml", "w", encoding='utf-8') as f:
                     yaml.dump(config, f, allow_unicode=True)
                return f"✅ 关注成功: {', '.join(added_names)}"
            else:
                return f"ℹ️ 已经关注过了: {name}"

    except Exception as e:
        logger.error(f"Command failed: {e}")
        return f"❌ 处理出错: {str(e)}"

@app.api_route("/api/wecom/callback", methods=["GET", "POST"])
async def wecom_callback(
    request: Request,
    msg_signature: str = Query(None),
    timestamp: str = Query(None),
    nonce: str = Query(None),
    echostr: str = Query(None)
):
    """Handle WeCom Validation and Messages."""
    wecom_cfg = config.get('notify', {}).get('wecom', {})
    token = wecom_cfg.get('token')
    aes_key = wecom_cfg.get('aes_key')
    corp_id = wecom_cfg.get('corp_id')
    
    if not token or not aes_key:
        logger.error("WeCom Token/AESKey not configured.")
        return Response("Config Error", status_code=500)
        
    try:
        crypto = WeChatCrypto(token, aes_key, corp_id)
    except Exception as e:
        logger.error(f"Crypto init failed: {e}")
        return Response("Crypto Init Failed", status_code=500)

    # 1. Verification (GET)
    if request.method == "GET":
        try:
            decrypted_echo = crypto.check_signature(msg_signature, timestamp, nonce, echostr)
            return Response(content=decrypted_echo)
        except InvalidSignatureException:
            raise HTTPException(status_code=403, detail="Invalid Signature")

    # 2. Message (POST)
    if request.method == "POST":
        try:
            body = await request.body()
            decrypted_xml = crypto.decrypt_message(body, msg_signature, timestamp, nonce)
            msg = parse_message(decrypted_xml)
            
            if msg.type == 'text':
                content = msg.content.strip()
                reply_content = await handle_wecom_command(content)
                
                reply = create_reply(reply_content, msg)
                xml_reply = reply.render()
                encypted_reply = crypto.encrypt_message(xml_reply, nonce, timestamp)
                return Response(content=encypted_reply, media_type="application/xml")
                
            return Response("success")
            
        except Exception as e:
            logger.error(f"WeCom Message Error: {e}")
            return Response("success") # Always return success to stop retries

# --- SPA & Static Files ---

# Mount static files (Vue Build)
if os.path.exists("web/dist"):
    app.mount("/assets", StaticFiles(directory="web/dist/assets"), name="assets")
    
    # Catch-all for SPA
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Allow API calls to pass through (handled above)
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
            
        # Serve index.html for everything else
        file_path = "web/dist/index.html"
        if os.path.exists(file_path):
             return FileResponse(file_path)
             
        return "Frontend build not found (web/dist/index.html missing)"

if __name__ == "__main__":
    import uvicorn
    # Allow running directly for debugging
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
