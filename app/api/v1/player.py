# -*- coding: utf-8 -*-
"""
播放路由 - 音频文件服务与播放代理

从 media.py 拆出（阶段 4.6）：播放域单一职责。
包含 [Fix C-02] 目录穿越防护（_get_allowed_media_roots / _is_path_contained）。

Author: google
Updated: 2026-08-13
"""
import os
import logging
from urllib.parse import quote
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from core.storage import get_storage_paths
from app.services.media_service import MediaService
from app.container import get_download_service
from app.dependencies import require_auth

router = APIRouter(dependencies=[Depends(require_auth)])
logger = logging.getLogger(__name__)


def _get_allowed_media_roots() -> list:
    """返回允许对外提供音频文件的根目录绝对路径列表。

    取自配置的 storage 段，并补上项目默认目录，避免用户未配置时把合法路径判成越权。

    Returns:
        去重后的绝对路径列表（已 realpath 解析，符号链接被展开）。
    """
    paths = get_storage_paths()
    candidates = [
        str(paths.cache_dir),
        str(paths.favorites_dir),
    ]
    if paths.library_dir:
        candidates.append(str(paths.library_dir))

    roots = []
    for candidate in candidates:
        if not candidate:
            continue
        resolved = os.path.realpath(os.path.abspath(candidate))
        if resolved not in roots:
            roots.append(resolved)
    return roots


def _is_path_contained(file_path: str) -> bool:
    """校验待返回的文件是否落在允许的媒体目录内（防 `../` 目录穿越）。

    使用 realpath 展开符号链接后再比较，并借助 os.path.commonpath 做真正的
    "父目录包含"判断，避免 `/data/audio_cache_evil` 被 `/data/audio_cache`
    前缀匹配误放行。

    Args:
        file_path: 待返回给客户端的文件路径（可能是相对路径）。

    Returns:
        True 表示路径合法且位于允许目录内。
    """
    if not file_path:
        return False

    resolved = os.path.realpath(os.path.abspath(file_path))

    for root in _get_allowed_media_roots():
        try:
            # commonpath 在不同盘符 (Windows) 或不同挂载点时会抛 ValueError
            if os.path.commonpath([resolved, root]) == root:
                return True
        except ValueError:
            continue
    return False


@router.get("/api/audio/{filename:path}")
async def serve_audio(
    filename: str,
    media_service: MediaService = Depends(MediaService),
    db: AsyncSession = Depends(get_async_session)
) -> Any:
    """提供音频文件"""
    try:
        file_path, song = await media_service.get_audio_path(filename, db)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="音频文件未找到")

        # [Fix C-02] 路径 containment 校验：`{filename:path}` 允许出现 `../`，
        # 必须确认最终解析出的物理路径仍落在允许的媒体目录内，否则拒绝。
        if not _is_path_contained(file_path):
            logger.warning(f"拒绝越权音频路径访问: filename={filename!r} resolved={file_path!r}")
            raise HTTPException(status_code=403, detail="非法的音频路径")

        media_type = "audio/mpeg"
        if filename.endswith(".flac"):
            media_type = "audio/flac"

        filename_encoded = quote(filename)
        return FileResponse(
            file_path,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename*=utf-8''{filename_encoded}"}
        )
    except HTTPException:
        # 上面主动抛出的 403/404 必须原样透传，否则会被下面的兜底分支吞成 500
        raise
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="音频文件未找到")
    except Exception as e:
        logger.error(f"提供音频错误: {e}")
        raise HTTPException(status_code=500, detail="服务器错误: 服务器内部错误, 请查看日志")


@router.get("/api/play/{source}/{id}")
async def play_proxy(source: str, id: str):
    """获取直接播放链接"""
    download_service = get_download_service()
    url = await download_service.get_play_url(source, id)

    if url:
        return RedirectResponse(url)

    return JSONResponse({"error": "链接未找到"}, status_code=404)
