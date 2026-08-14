from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_async_session
from core.security import hash_password, verify_password
import logging
import re
import time
import yaml
import os

# Imports from core/app
from core.config import CONFIG_FILE_PATH
from core.config_manager import get_config_manager
from app.schemas import LoginRequest, ChangePasswordRequest, UpdateProfileRequest, LoginResponse, AuthCheckResponse, ProfileStatsResponse, GenericActionResponse, UserResponse
from app.dependencies import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)

# 登录失败限速 (M3): username -> (失败次数, 锁定截止时间戳)。
# 单进程内有效 (inline 模式完全生效; arq 模式多 worker 下各进程独立计数,
# 属于尽力而为的缓解, 不替代 WAF/网关层防护)。
_LOGIN_FAILS: dict = {}
_LOGIN_MAX_FAILS = 5
_LOGIN_LOCK_SECONDS = 15 * 60


def _login_rate_limited(username: str) -> bool:
    """检查是否处于锁定状态 (锁定期间直接拒绝)。"""
    now = time.time()
    fails, lock_until = _LOGIN_FAILS.get(username, (0, 0))
    return lock_until > now


def _record_login_failure(username: str):
    """记录一次失败; 连续失败达阈值则锁定 15 分钟。"""
    now = time.time()
    fails, lock_until = _LOGIN_FAILS.get(username, (0, 0))
    if lock_until > now:
        return
    fails += 1
    if fails >= _LOGIN_MAX_FAILS:
        lock_until = now + _LOGIN_LOCK_SECONDS
        logger.warning(f"登录失败次数过多, 用户 {username!r} 已锁定 {_LOGIN_LOCK_SECONDS}s")
        fails = 0
    _LOGIN_FAILS[username] = (fails, lock_until)


def _record_login_success(username: str):
    """登录成功后清除失败记录。"""
    _LOGIN_FAILS.pop(username, None)


@router.post("/api/login", response_model=LoginResponse)
async def login(req: LoginRequest, request: Request):
    auth_cfg = get_config_manager().get('auth', {})
    if not auth_cfg.get('enabled', False):
         return {"success": True, "message": "鉴权已禁用"}

    if _login_rate_limited(req.username):
        raise HTTPException(status_code=429, detail="尝试次数过多, 请 15 分钟后再试")

    stored_password = auth_cfg.get('password') or ''
    # 校验通过 (兼容旧版明文配置); 命中即成功并清除失败计数
    if req.username == auth_cfg.get('username') and verify_password(req.password, stored_password):
        _record_login_success(req.username)
        request.session["user"] = req.username
        return {"success": True, "message": "登录成功"}

    _record_login_failure(req.username)
    raise HTTPException(status_code=401, detail="账号或密码错误")

@router.post("/api/logout", response_model=LoginResponse)
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out"}

@router.post("/api/update_profile", response_model=GenericActionResponse, dependencies=[Depends(require_auth)])
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
        raise HTTPException(status_code=500, detail="服务器内部错误, 请查看日志")

@router.post("/api/upload_avatar", response_model=GenericActionResponse, dependencies=[Depends(require_auth)])
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
        if not ext:
            ext = ".jpg"

        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(upload_dir, filename)

        # Save file asynchronously
        import aiofiles
        async with aiofiles.open(filepath, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await buffer.write(chunk)

        # Return URL
        # Assumption: /uploads is mounted in main.py
        file_url = f"/uploads/avatars/{filename}"

        return {"status": "success", "url": file_url}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload avatar failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed: 服务器内部错误, 请查看日志")

@router.post("/api/change_password", response_model=GenericActionResponse, dependencies=[Depends(require_auth)])
def change_password(req: ChangePasswordRequest, request: Request):
    auth_cfg = get_config_manager().get('auth', {})
    if not auth_cfg.get('enabled', False):
         raise HTTPException(status_code=400, detail="Auth not enabled")

    # 1. Verify old password (兼容旧版明文配置)
    if not verify_password(req.old_password, auth_cfg.get('password') or ''):
        raise HTTPException(status_code=401, detail="旧密码错误")

    # 2. Update config file (只替换 auth 段的 password, 兼容明文/哈希两种存量值)
    try:
        with open(CONFIG_FILE_PATH, "r", encoding='utf-8') as f:
            content = f.read()

        # 新密码落盘前先哈希, 避免明文写入 config.yaml (M3)
        new_hash = hash_password(req.new_password)
        pattern = re.compile(
            r'(^auth:\s*\n(?:[ \t]+.*\n)*?[ \t]+password:\s*)(["\']?)([^"\'\n]*)(["\']?)',
            re.MULTILINE,
        )

        if not re.search(pattern, content):
             logger.error("Could not find auth.password in config file to replace")
             raise Exception("Config file auth.password pattern mismatch")

        new_content = pattern.sub(
            f'\\1"{new_hash}"',
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
        raise HTTPException(status_code=500, detail="修改失败: 服务器内部错误, 请查看日志")

@router.get("/api/check_auth", response_model=AuthCheckResponse)
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


@router.get("/api/user", response_model=UserResponse, dependencies=[Depends(require_auth)])
def get_current_user(request: Request):
    """获取当前登录用户信息 (前端 stores/user.ts fetchUser 依赖)。

    阶段 4 验收发现：前端 `api/auth.ts getUser()` 调用 /api/user，
    但后端从未实现该端点，登录后 fetchUser 恒 404。
    此处补上与 check_auth 一致的用户解析逻辑。
    """
    auth_cfg = get_config_manager().get('auth', {})
    user = request.session.get("user")

    if not auth_cfg.get('enabled', False):
        # 鉴权禁用：与 check_auth 一致返回内置用户
        return {"username": "admin", "avatar": auth_cfg.get('avatar')}

    if not user:
        raise HTTPException(status_code=401, detail="未授权，请先登录")

    return {"username": user, "avatar": auth_cfg.get('avatar')}


@router.get("/api/profile_stats", response_model=ProfileStatsResponse, dependencies=[Depends(require_auth)])
async def profile_stats(db: AsyncSession = Depends(get_async_session)):
    """获取个人中心统计信息"""
    from sqlalchemy import func, select
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
