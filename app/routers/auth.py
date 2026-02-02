from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_async_session
import logging
import re
import yaml
import shutil
import os
import time

# Imports from core/app
from core.config import load_config, CONFIG_FILE_PATH
from core.config_manager import get_config_manager
from app.schemas import LoginRequest, ChangePasswordRequest, UpdateProfileRequest

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/api/login")
async def login(req: LoginRequest, request: Request):
    auth_cfg = get_config_manager().get('auth', {})
    if not auth_cfg.get('enabled', False):
         return {"success": True, "message": "鉴权已禁用"}
         
    if req.username == auth_cfg.get('username') and req.password == auth_cfg.get('password'):
        request.session["user"] = req.username
        return {"success": True, "message": "登录成功"}
    
    raise HTTPException(status_code=401, detail="账号或密码错误")

@router.post("/api/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}

@router.post("/api/update_profile")
def update_profile(req: UpdateProfileRequest, request: Request):
    auth_cfg = get_config_manager().get('auth', {})
    if not auth_cfg.get('enabled', False):
         raise HTTPException(status_code=400, detail="Auth not enabled")
    
    # Update config file
    try:
        with open(CONFIG_FILE_PATH, "r", encoding='utf-8') as f:
            content = f.read()
            
        # Update Username
        current_username = auth_cfg.get('username')
        if req.username and req.username != current_username:
             pattern = fr'(username:\s*)(["\']?)({re.escape(current_username)})(["\']?)'
             if re.search(pattern, content):
                 content = re.sub(pattern, f'\\1"{req.username}"', content, count=1)
        
        # Update Avatar (Safe Update via Dict Dump)
        # Re-read to be safe or use content? 
        # The regex replacement for username modified 'content'.
        # For avatar, if we use yaml.dump, we lose comments.
        # But 'add_artist' uses dump, so we compromised on comments.
        # To be safe and consistent with main.py logic:
        
        # 1. Update memory dict (which will be dumped)
        config_manager = get_config_manager()
        config_manager.data['auth']['username'] = req.username
        if req.avatar is not None:
            config_manager.data['auth']['avatar'] = req.avatar
            
        with open(CONFIG_FILE_PATH, "w", encoding='utf-8') as f:
            yaml.safe_dump(config_manager.data, f, allow_unicode=True, default_flow_style=False)
            
        # Update Session User if changed
        if req.username != request.session.get("user"):
            request.session["user"] = req.username
            
        return {"status": "success", "message": "个人资料已更新"}

    except Exception as e:
        logger.error(f"Failed to update profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/upload_avatar")
async def upload_avatar(request: Request, file: UploadFile = File(...)):
    """Upload user avatar"""
    auth_cfg = get_config_manager().get('auth', {})
    if not auth_cfg.get('enabled', False):
         raise HTTPException(status_code=400, detail="Auth not enabled")
    
    # Check session
    user = request.session.get("user")
    if not user:
         raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Only image files allowed")
            
        # Ensure dir exists
        if CONFIG_FILE_PATH.startswith("/config"):
             upload_dir = "/config/uploads/avatars"
        else:
             upload_dir = "uploads/avatars"
             
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate secure filename (UUID to avoid encoding issues)
        import uuid
        ext = os.path.splitext(file.filename)[1]
        if not ext: ext = ".jpg"
        
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(upload_dir, filename)
        
        # Save file
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Return URL
        # Assumption: /uploads is mounted in main.py
        file_url = f"/uploads/avatars/{filename}"
        
        return {"status": "success", "url": file_url}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload avatar failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/api/change_password")
def change_password(req: ChangePasswordRequest, request: Request):
    auth_cfg = get_config_manager().get('auth', {})
    if not auth_cfg.get('enabled', False):
         raise HTTPException(status_code=400, detail="Auth not enabled")
    
    # 1. Verify old password
    if req.old_password != auth_cfg.get('password'):
        raise HTTPException(status_code=401, detail="旧密码错误")
    
    # 2. Update config file
    try:
        with open(CONFIG_FILE_PATH, "r", encoding='utf-8') as f:
            content = f.read()
            
        # Check if password matches old password to be safe
        old_esc = re.escape(req.old_password)
        pattern = fr'(password:\s*)(["\']?)({old_esc})(["\']?)'
        
        if not re.search(pattern, content):
             logger.error("Could not find password in config file to replace")
             raise Exception("Config file password pattern mismatch")

        new_content = re.sub(
            pattern,
            f'\\1"{req.new_password}"',
            content,
            count=1 
        )
        
        with open(CONFIG_FILE_PATH, "w", encoding='utf-8') as f:
            f.write(new_content)
            
        # 3. Reload global config
        get_config_manager().reload()
        
        # 4. Logout user
        request.session.clear()
        
        return {"message": "密码修改成功，请重新登录"}
        
    except Exception as e:
        logger.error(f"Failed to change password: {e}")
        raise HTTPException(status_code=500, detail=f"修改失败: {str(e)}")

@router.get("/api/check_auth")
def check_auth(request: Request):
    auth_cfg = get_config_manager().get('auth', {})
    
    user = request.session.get("user")
    is_enabled = auth_cfg.get('enabled', False)

    if not is_enabled:
        return JSONResponse(
            content={"authenticated": True, "user": "admin", "enabled": False},
            headers={"Cache-Control": "no-store"}
        )
        
    return JSONResponse(
        content={
            "authenticated": bool(user), 
            "user": user, 
            "avatar": auth_cfg.get('avatar'),
            "enabled": True
        },
        headers={"Cache-Control": "no-store"}
    )


@router.get("/api/profile_stats")
async def profile_stats(db: AsyncSession = Depends(get_async_session)):
    """获取个人中心统计信息"""
    from sqlalchemy import func
    from app.models.song import Song
    from app.models.artist import Artist

    stats = {
        "artist_count": 0,
        "song_count": 0,
        "cache_size": "0 MB"
    }
    
    try:
        # 1. 歌手数量 (从 Artist 表)
        stmt_artist = select(func.count(Artist.id))
        res_artist = await db.execute(stmt_artist)
        stats["artist_count"] = res_artist.scalar() or 0
        
        # 2. 歌曲数量 (从 Song 表)
        stmt_song = select(func.count(Song.id))
        res_song = await db.execute(stmt_song)
        stats["song_count"] = res_song.scalar() or 0
        
        # 3. 计算缓存大小
        cache_dir = get_config_manager().get('storage', {}).get('cache_dir', 'audio_cache')
        total_size = 0
        if os.path.exists(cache_dir):
            for f in os.listdir(cache_dir):
                fp = os.path.join(cache_dir, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
            
            # 转换为人类可读格式
            if total_size < 1024 * 1024:
                stats["cache_size"] = f"{total_size / 1024:.1f} KB"
            elif total_size < 1024 * 1024 * 1024:
                stats["cache_size"] = f"{total_size / (1024 * 1024):.1f} MB"
            else:
                stats["cache_size"] = f"{total_size / (1024 * 1024 * 1024):.2f} GB"
                
    except Exception as e:
        logger.warning(f"获取统计信息失败: {e}")
    
    return stats
